from __future__ import annotations

from typing import Any

from core.sql_validator import validate_sql_text


class SQLSelfReviewer:
    """Rule-based self reviewer. LLM-based review can be added later."""

    def review_sql_draft(self, sql_text: str, shape: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
        validator = validate_sql_text(sql_text, shape, cfg.get("generation", {}))
        status = "pass" if validator["valid"] else "revise"
        return {
            "status": status,
            "validator": validator,
            "notes": validator.get("issues", []),
        }
