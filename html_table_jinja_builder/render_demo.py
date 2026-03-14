"""Render a generated template with JSON data (Jinja-like placeholders)."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def render_template(template_path: Path, data_path: Path, out_path: Path) -> None:
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    template_text = template_path.read_text(encoding="utf-8")
    data = json.loads(data_path.read_text(encoding="utf-8"))

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(data.get(key, match.group(0)))

    rendered = PLACEHOLDER_RE.sub(repl, template_text)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render generated template with JSON data")
    parser.add_argument("--template", required=True, help="Path to template HTML.j2")
    parser.add_argument("--data", required=True, help="Path to mock data JSON")
    parser.add_argument("--out", required=True, help="Path to rendered preview HTML")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    render_template(Path(args.template), Path(args.data), Path(args.out))
    print("Rendered preview HTML generated")
