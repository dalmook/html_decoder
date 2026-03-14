from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def enrich_context(base_context: dict[str, Any], row_count: int, sql_file: Path) -> dict[str, Any]:
    out = dict(base_context)
    out["report_meta"] = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "row_count": row_count,
        "sql_file": str(sql_file),
    }
    return out
