from __future__ import annotations

import re
from typing import Any


FORBIDDEN = ["INSERT", "UPDATE", "DELETE", "MERGE", "DROP", "TRUNCATE", "ALTER", "CREATE"]


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def validate_sql_text(sql_text: str, shape: dict[str, Any], generation_cfg: dict[str, Any]) -> dict[str, Any]:
    sql = _strip_comments(sql_text).strip()
    upper = sql.upper()
    issues: list[str] = []

    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        issues.append("SQL must start with SELECT or WITH")

    # multi statement check
    cleaned = sql.rstrip().rstrip(";")
    if ";" in cleaned:
        issues.append("Multiple statements are not allowed")

    for kw in FORBIDDEN:
        if re.search(rf"\b{kw}\b", upper):
            issues.append(f"Forbidden keyword detected: {kw}")

    measure_candidates = shape.get("recommended_shape_wide", {}).get("measure_columns", [])
    if measure_candidates:
        present = sum(1 for c in measure_candidates if c.upper() in upper)
        ratio = present / len(measure_candidates)
        if ratio < 0.34:
            issues.append("Too few measure columns referenced in SQL")

    if generation_cfg.get("forbid_dml", True):
        for kw in ["INSERT", "UPDATE", "DELETE", "MERGE"]:
            if re.search(rf"\b{kw}\b", upper):
                issues.append(f"DML forbidden by config: {kw}")

    if "TO_CHAR(" in upper:
        issues.append("Avoid TO_CHAR formatting in SQL. Return raw numeric values.")

    return {"valid": len(issues) == 0, "issues": issues}
