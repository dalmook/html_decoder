from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from core.formatters import FILTERS


TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_\.]*)(?:\s*\|\s*([a-zA-Z_][a-zA-Z0-9_]*))?\s*\}\}")


def _resolve_key(context: dict[str, Any], key: str) -> Any:
    if "." not in key:
        return context.get(key)
    cur: Any = context
    for part in key.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def _simple_render(template_text: str, context: dict[str, Any]) -> str:
    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        filter_name = m.group(2)
        val = _resolve_key(context, key)
        if filter_name in FILTERS:
            val = FILTERS[filter_name](val)
        return "" if val is None else str(val)

    return TOKEN_RE.sub(repl, template_text)


def render_report(template_text: str, context: dict[str, Any], logger=None) -> str:
    try:
        from jinja2 import BaseLoader, Environment

        env = Environment(loader=BaseLoader(), autoescape=False)
        for name, fn in FILTERS.items():
            env.filters[name] = fn
        template = env.from_string(template_text)
        return template.render(**context)
    except Exception as exc:  # fallback for missing jinja2 or runtime errors
        if logger:
            logger.warning("RENDER_FALLBACK", "Jinja2 unavailable/failure. Fallback renderer used.", error=str(exc))
        return _simple_render(template_text, context)


def write_error_html(out_path: Path, message: str) -> None:
    html = f"<html><body><p style='color:red'>DB 오류: {message}</p></body></html>"
    out_path.write_text(html, encoding="utf-8")
