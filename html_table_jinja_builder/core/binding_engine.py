from __future__ import annotations

import re
from typing import Any

from core.logger import RenderLogger


SAFE_FUNCS = {
    "add": lambda a, b: (a or 0) + (b or 0),
    "sub": lambda a, b: (a or 0) - (b or 0),
    "mul": lambda a, b: (a or 0) * (b or 0),
    "div": lambda a, b: None if not b else (a or 0) / b,
    "ratio": lambda a, b: None if not b else ((a or 0) / b) * 100,
    "days_of_inventory": lambda inv, sales, days: None if not sales else ((inv or 0) / sales) * (days or 0),
}


def _to_number(v: Any) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).replace(",", "").replace("%", "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _match_row(records: list[dict[str, Any]], row_keys: dict[str, Any]) -> dict[str, Any] | None:
    for row in records:
        ok = True
        for _, val in row_keys.items():
            if val is None:
                continue
            if str(val) not in {str(v) for v in row.values()}:
                ok = False
                break
        if ok:
            return row
    return None


def _parse_formula_hint(formula_hint: str) -> tuple[str, list[str]] | None:
    # accepts add(a,b), ratio(a,b), days_of_inventory(inv,sales,30)
    m = re.match(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\((.*)\)\s*$", formula_hint or "")
    if not m:
        return None
    fn = m.group(1)
    args = [x.strip() for x in m.group(2).split(",") if x.strip()]
    return (fn, args)


def _resolve_token(token: str, context: dict[str, Any], row: dict[str, Any]) -> float | None:
    if token in context:
        return _to_number(context[token])
    if token in row:
        return _to_number(row[token])
    if re.match(r"^-?\d+(?:\.\d+)?$", token):
        return float(token)
    return None


def build_binding_context(
    records: list[dict[str, Any]],
    binding_spec: dict[str, Any],
    logger: RenderLogger,
    fail_on_missing: bool,
) -> tuple[dict[str, Any], dict[str, int]]:
    context: dict[str, Any] = {}
    success = 0
    warns = 0
    computed_placeholders = []

    # direct first
    for ph, spec in binding_spec.items():
        if spec.get("binding_type") != "direct":
            continue
        lookup = spec.get("lookup", {})
        row = _match_row(records, lookup.get("row_keys", {}))
        col = lookup.get("value_column")
        value = None if row is None else row.get(col) or row.get(str(col).upper())
        context[ph] = value
        if value is None:
            warns += 1
            logger.warning("BIND_DIRECT_MISS", f"Direct binding missed for {ph}", placeholder=ph)
            if fail_on_missing:
                raise ValueError(f"Missing value for placeholder: {ph}")
        else:
            success += 1

    # computed second
    for ph, spec in binding_spec.items():
        if spec.get("binding_type") != "computed":
            continue
        computed_placeholders.append(ph)
        formula_hint = spec.get("formula_hint") or ""
        parsed = _parse_formula_hint(formula_hint)
        row = _match_row(records, spec.get("lookup", {}).get("row_keys", {})) or {}

        if not parsed:
            warns += 1
            context[ph] = context.get(ph)
            logger.warning("BIND_COMPUTED_PARSE_SKIP", f"Cannot parse formula for {ph}", placeholder=ph, formula_hint=formula_hint)
            continue

        fn_name, tokens = parsed
        fn = SAFE_FUNCS.get(fn_name)
        if not fn:
            warns += 1
            logger.warning("BIND_COMPUTED_FUNC_SKIP", f"Unsupported formula function for {ph}", placeholder=ph, formula=fn_name)
            continue

        args = [_resolve_token(t, context, row) for t in tokens]
        value = fn(*args)
        context[ph] = value
        if value is None:
            warns += 1
            logger.warning("BIND_COMPUTED_NULL", f"Computed binding returned null for {ph}", placeholder=ph, tokens=tokens)
        else:
            success += 1

        if spec.get("needs_review"):
            warns += 1
            logger.warning("BIND_NEEDS_REVIEW", f"Binding marked needs_review: {ph}", placeholder=ph)

    return context, {"binding_success_count": success, "binding_warning_count": warns, "computed_count": len(computed_placeholders)}
