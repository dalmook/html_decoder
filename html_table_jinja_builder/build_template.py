"""CLI to build Jinja2 template/data contract/mock data from pasted HTML table."""

from __future__ import annotations

import argparse
from pathlib import Path

from table_builder import (
    build_virtual_grid,
    detect_candidate_cells,
    generate_data_contract,
    generate_mock_data,
    generate_template,
    parse_html_tables,
    write_json,
)


def build_template(input_path: Path, output_dir: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(f"Input HTML not found: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    html_text = input_path.read_text(encoding="utf-8")

    soup, tables = parse_html_tables(html_text)
    if not tables:
        raise ValueError("No <table> tag found in input HTML.")

    all_rows = []
    for table_index, table in enumerate(tables):
        cell_metas = build_virtual_grid(table, table_index)
        all_rows.extend(detect_candidate_cells(cell_metas))

    template_text = generate_template(soup, all_rows)
    data_contract = generate_data_contract(all_rows)
    mock_data = generate_mock_data(data_contract)

    (output_dir / "template.html.j2").write_text(template_text, encoding="utf-8")
    write_json(output_dir / "data_contract.json", data_contract)
    write_json(output_dir / "mock_data.json", mock_data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Jinja2 HTML template from table HTML")
    parser.add_argument("--input", required=True, help="Path to input HTML file")
    parser.add_argument("--output-dir", required=True, help="Output directory path")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    build_template(Path(args.input), Path(args.output_dir))
    print("Generated template.html.j2, data_contract.json, mock_data.json")
