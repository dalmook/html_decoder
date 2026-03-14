from __future__ import annotations

import json
import re
from typing import Any


def _extract_sql_fence(text: str) -> str:
    m = re.search(r"```sql\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"```\s*(.*?)```", text, flags=re.DOTALL)
    if m2:
        return m2.group(1).strip()
    return text.strip()


def parse_generation_response(text: str) -> tuple[dict[str, Any], bool]:
    """Return parsed object and fallback_used flag."""
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and "sql" in obj:
            return obj, False
    except Exception:
        pass

    sql_text = _extract_sql_fence(text)
    return {
        "sql": sql_text,
        "assumptions": ["response JSON parsing failed; fallback SQL extraction used"],
        "expected_output_shape": {
            "grain_keys": [],
            "dimension_columns": [],
            "measure_columns": [],
        },
        "binding_notes": [],
        "risks": ["LLM did not return strict JSON response"],
    }, True
