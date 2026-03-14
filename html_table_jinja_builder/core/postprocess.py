from __future__ import annotations

import math
from typing import Any


def _clean_val(v: Any, strip_strings: bool) -> Any:
    if isinstance(v, str):
        v2 = v.strip() if strip_strings else v
        if v2 == "":
            return None
        return v2
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def normalize_records(records: list[dict[str, Any]], case_insensitive_columns: bool, strip_strings: bool) -> list[dict[str, Any]]:
    out = []
    for row in records:
        new_row = {}
        for k, v in row.items():
            key = k.strip()
            key = key.upper() if case_insensitive_columns else key
            new_row[key] = _clean_val(v, strip_strings)
        out.append(new_row)
    return out


def normalize_dataframe(records: list[dict[str, Any]], runtime_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    return normalize_records(
        records,
        case_insensitive_columns=bool(runtime_cfg.get("case_insensitive_columns", True)),
        strip_strings=bool(runtime_cfg.get("strip_strings", True)),
    )
