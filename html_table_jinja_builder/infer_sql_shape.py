"""CLI: infer SQL shape and bindings from stage-1 outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

from shape_advisors import RuleBasedShapeAdvisor
from sql_shape_builder import load_contract, run_rule_based, write_sql_shape


class _RuleEngine:
    @staticmethod
    def run_rule_based(context):
        return run_rule_based(context)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Infer SQL shape from template + contract")
    p.add_argument("--template", required=True, help="Path to template.html.j2")
    p.add_argument("--contract", required=True, help="Path to data_contract.json")
    p.add_argument("--outdir", required=True, help="Output directory")
    p.add_argument("--prefer-shape", choices=["wide", "long", "auto"], default="auto")
    p.add_argument("--period-patterns", default="quarter,week,month", help="comma-separated period pattern names")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    contract = load_contract(Path(args.contract))
    context = {
        "contract": contract,
        "template_name": Path(args.template).name,
        "prefer_shape": args.prefer_shape,
        "period_patterns": [x.strip() for x in args.period_patterns.split(",") if x.strip()],
    }

    advisor = RuleBasedShapeAdvisor(engine=_RuleEngine())
    result = advisor.advise(context)

    write_sql_shape(outdir / "sql_shape.json", result["sql_shape"])
    write_sql_shape(outdir / "binding_spec.json", result["binding_spec"])

    print("[OK] Generated output/sql_shape.json")
    print("[OK] Generated output/binding_spec.json")


if __name__ == "__main__":
    main()
