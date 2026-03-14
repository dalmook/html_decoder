"""CLI: generate SQL-writing docs from inferred sql_shape.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sql_shape_builder import load_contract, write_mapping_guide, write_sql_prompt, write_sql_skeleton


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate sql_prompt/sql_skeleton/mapping_guide docs")
    p.add_argument("--shape", required=True, help="Path to sql_shape.json")
    p.add_argument("--contract", required=True, help="Path to data_contract.json")
    p.add_argument("--outdir", required=True, help="Output directory")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    shape = json.loads(Path(args.shape).read_text(encoding="utf-8"))
    contract = load_contract(Path(args.contract))
    binding_spec_path = outdir / "binding_spec.json"
    binding_spec = json.loads(binding_spec_path.read_text(encoding="utf-8")) if binding_spec_path.exists() else {}

    write_sql_prompt(shape, contract, outdir / "sql_prompt.md")
    write_sql_skeleton(shape, outdir / "sql_skeleton.sql")
    write_mapping_guide(shape, contract, binding_spec, outdir / "mapping_guide.md")

    print("[OK] Generated output/sql_prompt.md")
    print("[OK] Generated output/sql_skeleton.sql")
    print("[OK] Generated output/mapping_guide.md")


if __name__ == "__main__":
    main()
