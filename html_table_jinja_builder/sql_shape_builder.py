"""Stage-2 analyzers and generators: template requirement -> SQL shape/docs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

PERIOD_PATTERNS = {
    "quarter": re.compile(r"^(?:\d{1,2}(?:\.\d+)?Q|\d{4}Q[1-4]|\d{4}\.\dQ)$", re.IGNORECASE),
    "week": re.compile(r"^(?:\d{2}\.W\d{1,2}|W\d{1,2}|\d{4}W\d{1,2})$", re.IGNORECASE),
    "month": re.compile(r"^(?:\d{1,2}월|\d{4}-\d{2}|\d{6}|\d{4}\.\d{2})$", re.IGNORECASE),
}
TOTAL_PATTERNS = re.compile(r"\b(total|ttl|합계|subtotal|소계)\b", re.IGNORECASE)
DELTA_PATTERNS = re.compile(r"(전주대비|증감|차이|delta|variance|vs)", re.IGNORECASE)
MEASURE_PATTERNS = re.compile(r"(판매|순생산|재고|매출|이익|margin|risk|wip|ratio|마진|입고|출고)", re.IGNORECASE)
PERCENT_PATTERN = re.compile(r"^-?\d+(?:\.\d+)?%$")
NUM_PATTERN = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$|^-?\d+(?:\.\d+)?$")


def load_contract(contract_path: Path) -> dict[str, Any]:
    if not contract_path.exists():
        raise FileNotFoundError(f"Contract file not found: {contract_path}")
    return json.loads(contract_path.read_text(encoding="utf-8"))


def load_template(template_path: Path) -> str:
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def _to_num(a1: str) -> tuple[int, int]:
    m = re.match(r"^([A-Z]+)(\d+)$", a1)
    if not m:
        return (999, 999)
    letters, r = m.groups()
    col = 0
    for c in letters:
        col = col * 26 + (ord(c) - 64)
    return (int(r), col)


def _detect_period_token(text: str, enabled_patterns: list[str]) -> tuple[bool, str | None]:
    for name in enabled_patterns:
        p = PERIOD_PATTERNS.get(name)
        if p and p.match(text):
            return True, name
    return False, None


def classify_placeholders(contract: dict[str, Any], period_patterns: list[str]) -> dict[str, Any]:
    groups: dict[str, list[str]] = {
        "label_header": [],
        "period": [],
        "numeric_value": [],
        "total_subtotal": [],
        "delta_variance": [],
        "computed": [],
        "text": [],
    }

    details: dict[str, dict[str, Any]] = {}
    all_cells = sorted(contract.get("all_cells", []), key=lambda x: _to_num(x.get("a1_addr", "")))
    value_cells = sorted(contract.get("candidate_cells", []), key=lambda x: _to_num(x.get("a1_addr", "")))

    for row in all_cells:
        text = (row.get("normalized_text") or "").strip()
        is_period, period_kind = _detect_period_token(text, period_patterns)
        if not text:
            continue
        if row.get("tag") == "th" or row.get("rowspan", 1) > 1 or row.get("colspan", 1) > 1:
            groups["label_header"].append(text)
        if is_period:
            groups["period"].append(text)
        if TOTAL_PATTERNS.search(text):
            groups["total_subtotal"].append(text)
        if DELTA_PATTERNS.search(text):
            groups["delta_variance"].append(text)
        if MEASURE_PATTERNS.search(text):
            groups["computed" if "ratio" in text.lower() or "율" in text else "text"].append(text)

    for row in value_cells:
        placeholder = row.get("placeholder")
        text = (row.get("normalized_text") or "").strip()
        detected = row.get("detected_type", "text")
        is_period, period_kind = _detect_period_token(text, period_patterns)

        role = "numeric_value"
        confidence = 0.65
        if is_period:
            role = "period"
            confidence = 0.9
        elif TOTAL_PATTERNS.search(text):
            role = "total_subtotal"
            confidence = 0.85
        elif DELTA_PATTERNS.search(text):
            role = "delta_variance"
            confidence = 0.8
        elif detected in {"number", "percent"} or NUM_PATTERN.match(text):
            role = "numeric_value"
            confidence = 0.92 if detected == "number" else 0.9
        elif PERCENT_PATTERN.match(text) or "율" in text:
            role = "computed"
            confidence = 0.78
        else:
            role = "text"

        groups[role].append(placeholder)
        details[placeholder] = {
            "placeholder": placeholder,
            "a1_addr": row.get("a1_addr"),
            "original_text": row.get("original_text"),
            "detected_type": detected,
            "detected_role": role,
            "period_kind": period_kind,
            "confidence": round(confidence, 2),
        }

    for k, vals in groups.items():
        # de-dup while preserving order
        seen = set()
        dedup = []
        for v in vals:
            if v in seen:
                continue
            seen.add(v)
            dedup.append(v)
        groups[k] = dedup

    return {"placeholder_groups": groups, "placeholder_details": details}


def infer_layout(contract: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    all_cells = contract.get("all_cells", [])
    period_headers = set(classification["placeholder_groups"].get("period", []))

    header_rows = sorted(
        {c.get("a1_addr", "A1")[1:] for c in all_cells if c.get("tag") == "th"}
    )
    header_rows_num = [int(r) for r in header_rows if str(r).isdigit()]

    header_cols = sorted(
        {
            re.sub(r"\d+", "", c.get("a1_addr", "A1"))
            for c in all_cells
            if (c.get("colspan", 1) > 1 or c.get("rowspan", 1) > 1 or c.get("tag") == "th")
        }
    )

    # infer period direction by checking whether period-like labels appear mostly in same row or same col
    period_label_cells = [c for c in all_cells if c.get("normalized_text") in period_headers]
    rows = [int(re.sub(r"[A-Z]+", "", c.get("a1_addr", "A1"))) for c in period_label_cells if c.get("a1_addr")]
    cols = [re.sub(r"\d+", "", c.get("a1_addr", "A1")) for c in period_label_cells if c.get("a1_addr")]

    period_direction = "mixed"
    if rows and len(set(rows)) == 1 and len(set(cols)) > 1:
        period_direction = "horizontal"
    elif cols and len(set(cols)) == 1 and len(set(rows)) > 1:
        period_direction = "vertical"

    measure_direction = "vertical"
    if period_direction == "vertical":
        measure_direction = "horizontal"

    return {
        "header_rows": header_rows_num or [1, 2],
        "header_cols": header_cols[:2] if header_cols else ["A", "B"],
        "period_direction": period_direction,
        "measure_direction": measure_direction,
    }


def infer_shape_candidates(contract: dict[str, Any], classification: dict[str, Any], layout: dict[str, Any]) -> dict[str, Any]:
    candidate_cells = contract.get("candidate_cells", [])
    numeric_placeholders = set(classification["placeholder_groups"].get("numeric_value", []))

    measure_columns = []
    for c in candidate_cells:
        if c.get("placeholder") in numeric_placeholders:
            measure_columns.append(c.get("placeholder"))

    wide = {
        "description": "가로 기간 + 행 차원 중심의 wide 결과셋 권장",
        "grain_keys": ["PERIOD", "BUSINESS_UNIT", "PRODUCT_GROUP"],
        "dimension_columns": ["PERIOD", "BUSINESS_UNIT", "PRODUCT_GROUP"],
        "measure_columns": ["SALES", "OPERATING_PROFIT", "MARGIN_PCT"],
        "example_rows": [
            {
                "PERIOD": "2026Q1",
                "BUSINESS_UNIT": "DRAM",
                "PRODUCT_GROUP": "Server",
                "SALES": 1250,
                "OPERATING_PROFIT": 210,
                "MARGIN_PCT": 16.8,
            }
        ],
    }

    long = {
        "description": "측정항목을 행으로 세운 long 결과셋 권장",
        "grain_keys": ["PERIOD", "BUSINESS_UNIT", "PRODUCT_GROUP", "MEASURE"],
        "dimension_columns": ["PERIOD", "BUSINESS_UNIT", "PRODUCT_GROUP"],
        "pivot_key_column": "MEASURE",
        "value_column": "VALUE",
        "example_rows": [
            {
                "PERIOD": "2026Q1",
                "BUSINESS_UNIT": "DRAM",
                "PRODUCT_GROUP": "Server",
                "MEASURE": "SALES",
                "VALUE": 1250,
            }
        ],
    }

    return {
        "recommended_shape_wide": wide,
        "recommended_shape_long": long,
        "numeric_placeholder_count": len(measure_columns),
        "layout_hint": layout,
    }


def _find_row_labels(all_cells: list[dict[str, Any]], target_row_num: int) -> dict[str, str]:
    labels = {}
    for c in all_cells:
        a1 = c.get("a1_addr", "")
        m = re.match(r"^([A-Z]+)(\d+)$", a1)
        if not m:
            continue
        col, row = m.group(1), int(m.group(2))
        if row == target_row_num and col in {"A", "B"} and c.get("normalized_text"):
            labels[f"ROW_KEY_{col}"] = c["normalized_text"]
    return labels


def _find_col_headers(all_cells: list[dict[str, Any]], target_col: str) -> dict[str, str]:
    headers = {}
    for c in all_cells:
        a1 = c.get("a1_addr", "")
        m = re.match(r"^([A-Z]+)(\d+)$", a1)
        if not m:
            continue
        col, row = m.group(1), int(m.group(2))
        if col == target_col and row <= 2 and c.get("normalized_text"):
            headers[f"HEADER_R{row}"] = c["normalized_text"]
    return headers


def build_render_bindings(contract: dict[str, Any], classification: dict[str, Any], prefer_shape: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    all_cells = contract.get("all_cells", [])
    rows = contract.get("candidate_cells", [])
    details = classification["placeholder_details"]

    render_bindings = []
    binding_spec: dict[str, Any] = {}

    for row in rows:
        placeholder = row.get("placeholder")
        a1 = row.get("a1_addr", "")
        m = re.match(r"^([A-Z]+)(\d+)$", a1)
        if not m:
            continue
        col, rnum = m.group(1), int(m.group(2))
        row_keys = _find_row_labels(all_cells, rnum)
        col_headers = _find_col_headers(all_cells, col)

        role = details.get(placeholder, {}).get("detected_role", "numeric_value")
        fmt = row.get("detected_type", "text")
        confidence = details.get(placeholder, {}).get("confidence", 0.6)

        is_computed = role in {"computed", "delta_variance"} or fmt == "percent"
        binding_type = "computed" if is_computed else "direct"

        expected = {
            "shape": "wide" if prefer_shape in {"wide", "auto"} else "long",
            "row_filter": row_keys,
            "column": col_headers.get("HEADER_R2", "VALUE"),
            "period": col_headers.get("HEADER_R1", "PERIOD"),
        }

        render_bindings.append({"placeholder": placeholder, "expected_source": expected, "confidence": confidence})
        binding_spec[placeholder] = {
            "binding_type": binding_type,
            "source_shape": expected["shape"],
            "lookup": {
                "row_keys": row_keys,
                "column_headers": col_headers,
                "value_column": expected["column"],
            },
            "format_hint": fmt,
            "confidence": confidence,
            "needs_review": bool(is_computed and confidence < 0.9),
            "formula_hint": "(분자/분모) 또는 증감식 점검 필요" if is_computed else None,
        }

    return render_bindings, binding_spec


def write_sql_shape(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_rule_based(context: dict[str, Any]) -> dict[str, Any]:
    contract = context["contract"]
    template_name = context["template_name"]
    prefer_shape = context.get("prefer_shape", "auto")
    period_patterns = context.get("period_patterns", ["quarter", "week", "month"])

    classification = classify_placeholders(contract, period_patterns)
    layout = infer_layout(contract, classification)
    shapes = infer_shape_candidates(contract, classification, layout)
    render_bindings, binding_spec = build_render_bindings(contract, classification, prefer_shape)

    placeholders = [r.get("placeholder") for r in contract.get("candidate_cells", []) if r.get("placeholder")]

    sql_shape = {
        "template_name": template_name,
        "placeholders": placeholders,
        "placeholder_groups": classification["placeholder_groups"],
        "detected_layout": layout,
        "recommended_shape_wide": shapes["recommended_shape_wide"],
        "recommended_shape_long": shapes["recommended_shape_long"],
        "render_bindings": render_bindings,
    }

    return {
        "sql_shape": sql_shape,
        "binding_spec": binding_spec,
    }


def write_sql_prompt(shape: dict[str, Any], contract: dict[str, Any], out_path: Path) -> None:
    wide = shape["recommended_shape_wide"]
    long_shape = shape["recommended_shape_long"]
    layout = shape["detected_layout"]

    lines = [
        "# SQL 작성 프롬프트",
        "",
        "## 템플릿이 요구하는 최종 데이터 구조",
        f"- 템플릿명: `{shape['template_name']}`",
        f"- 권장 레이아웃: 기간방향 `{layout['period_direction']}`, 측정치방향 `{layout['measure_direction']}`",
        f"- Placeholder 개수: {len(shape.get('placeholders', []))}",
        "",
        "## 권장 Wide Shape",
        f"- Grain: {', '.join(wide['grain_keys'])}",
        f"- Dimension 컬럼: {', '.join(wide['dimension_columns'])}",
        f"- Measure 컬럼: {', '.join(wide['measure_columns'])}",
        "",
        "## 권장 Long Shape",
        f"- Grain: {', '.join(long_shape['grain_keys'])}",
        f"- Pivot key: {long_shape['pivot_key_column']}",
        f"- Value 컬럼: {long_shape['value_column']}",
        "",
        "## 기간 컬럼 후보",
        "- WORKDATE, WEEK_CD, QUARTER, YM",
        "",
        "## 주의사항",
        "- NULL 처리(NVL/COALESCE) 적용",
        "- 숫자/소수점/천단위 포맷은 Python/Jinja에서 처리 권장",
        "- SQL은 raw numeric 반환 권장",
        "- 최신주/TTL/전주대비 같은 파생값은 SQL 또는 Python 후처리 가능",
        "",
        "## 예시 결과 행",
        "```json",
        json.dumps(wide["example_rows"], ensure_ascii=False, indent=2),
        "```",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_sql_skeleton(shape: dict[str, Any], out_path: Path) -> None:
    lines = [
        "-- SQL Skeleton (Oracle-friendly)",
        "-- 목적: 템플릿 placeholder 바인딩 가능한 결과셋 준비",
        "",
        "/* Wide Shape 버전 */",
        "WITH base AS (",
        "    SELECT",
        "        /* TODO: 실제 소스 컬럼으로 교체 */",
        "        PERIOD, BUSINESS_UNIT, PRODUCT_GROUP,",
        "        SALES, OPERATING_PROFIT, MARGIN_PCT",
        "    FROM your_source",
        ")",
        "SELECT",
        "    PERIOD, BUSINESS_UNIT, PRODUCT_GROUP,",
        "    SALES, OPERATING_PROFIT, MARGIN_PCT",
        "FROM base;",
        "",
        "/* Long Shape 버전 */",
        "WITH base AS (",
        "    SELECT PERIOD, BUSINESS_UNIT, PRODUCT_GROUP, SALES, OPERATING_PROFIT, MARGIN_PCT",
        "    FROM your_source",
        "), unpivoted AS (",
        "    SELECT PERIOD, BUSINESS_UNIT, PRODUCT_GROUP, 'SALES' AS MEASURE, SALES AS VALUE FROM base",
        "    UNION ALL",
        "    SELECT PERIOD, BUSINESS_UNIT, PRODUCT_GROUP, 'OPERATING_PROFIT' AS MEASURE, OPERATING_PROFIT AS VALUE FROM base",
        "    UNION ALL",
        "    SELECT PERIOD, BUSINESS_UNIT, PRODUCT_GROUP, 'MARGIN_PCT' AS MEASURE, MARGIN_PCT AS VALUE FROM base",
        ")",
        "SELECT * FROM unpivoted;",
        "",
        "-- placeholder 대응은 output/binding_spec.json 참조",
    ]
    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_mapping_guide(shape: dict[str, Any], contract: dict[str, Any], binding_spec: dict[str, Any], out_path: Path) -> None:
    details = {r.get("placeholder"): r for r in contract.get("candidate_cells", [])}

    lines = [
        "# Mapping Guide",
        "",
        "| placeholder | original_text | detected_role | expected_period | expected_measure | binding_type | confidence | review_note |",
        "|---|---|---|---|---|---|---:|---|",
    ]

    for b in shape.get("render_bindings", []):
        ph = b["placeholder"]
        spec = binding_spec.get(ph, {})
        row = details.get(ph, {})
        expected = b.get("expected_source", {})
        note = "검토 필요" if spec.get("needs_review") else "-"
        role = "computed" if spec.get("binding_type") == "computed" else row.get("detected_type", "text")

        lines.append(
            f"| {ph} | {row.get('original_text','')} | {role} | {expected.get('period','')} | {expected.get('column','')} | {spec.get('binding_type','direct')} | {b.get('confidence',0):.2f} | {note} |"
        )

    out_path.write_text("\n".join(lines), encoding="utf-8")
