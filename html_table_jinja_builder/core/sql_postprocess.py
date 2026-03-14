from __future__ import annotations

import re


def postprocess_sql(sql_text: str) -> str:
    sql = sql_text.strip()
    sql = re.sub(r"^```sql\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"^```\s*", "", sql)
    sql = re.sub(r"```$", "", sql).strip()
    # keep single trailing semicolon removed for run-time compatibility
    sql = sql.rstrip(";").strip()
    return sql + "\n"
