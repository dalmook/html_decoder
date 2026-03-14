from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any

from core.binding_engine import build_binding_context
from core.context_builder import enrich_context
from core.loaders import load_json, load_report_assets, load_sql_text, merge_env_overrides
from core.logger import RenderLogger
from core.postprocess import normalize_dataframe
from core.render_engine import render_report, write_error_html
from db.oracle_runner import execute_query
from providers.sql_provider import ManualSQLProvider


def _default_path(cfg: dict[str, Any], cli_value: str | None, key_path: tuple[str, ...], fallback: str) -> Path:
    if cli_value:
        return Path(cli_value)
    cur = cfg
    for k in key_path:
        cur = cur.get(k, {}) if isinstance(cur, dict) else {}
    if isinstance(cur, str) and cur:
        return Path(cur)
    return Path(fallback)


def _write_preview(records: list[dict[str, Any]], outdir: Path) -> None:
    csv_path = outdir / "query_result_preview.csv"
    json_path = outdir / "query_result_preview.json"
    json_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        if not records:
            f.write("")
            return
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def write_debug_outputs(outdir: Path, context: dict[str, Any]) -> None:
    (outdir / "final_context.json").write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run SQL + binding + template rendering pipeline")
    p.add_argument("--sql", help="SQL file path")
    p.add_argument("--template", help="Template path")
    p.add_argument("--contract", help="Contract path")
    p.add_argument("--shape", help="Shape path")
    p.add_argument("--binding", help="Binding spec path")
    p.add_argument("--config", default="config/report_config.json", help="Config path")
    p.add_argument("--out", help="Final output html")
    p.add_argument("--mock-csv", help="Mock CSV input instead of DB query")
    p.add_argument("--fail-on-missing", action="store_true")
    p.add_argument("--verbose", action="store_true")
    p.add_argument("--error-html", action="store_true", help="Write error HTML on DB failure")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    logger = RenderLogger()

    config = load_json(Path(args.config))
    config = merge_env_overrides(config, dict(os.environ))

    sql_path = _default_path(config, args.sql, ("runtime", "sql_path"), "sql/user_query.sql")
    template_path = _default_path(config, args.template, ("render", "template_path"), "output/template.html.j2")
    contract_path = _default_path(config, args.contract, ("runtime", "contract_path"), "output/data_contract.json")
    shape_path = _default_path(config, args.shape, ("runtime", "shape_path"), "output/sql_shape.json")
    binding_path = _default_path(config, args.binding, ("runtime", "binding_path"), "output/binding_spec.json")
    out_path = _default_path(config, args.out, ("render", "default_output_path"), "output/final_report.html")

    outdir = out_path.parent
    outdir.mkdir(parents=True, exist_ok=True)

    try:
        assets = load_report_assets(template_path, contract_path, shape_path, binding_path)
        sql_text = ManualSQLProvider().get_sql(sql_path)

        records_raw = execute_query(sql_text, config.get("db", {}), mock_csv=args.mock_csv)
        records = normalize_dataframe(records_raw, config.get("runtime", {}))

        context, metrics = build_binding_context(records, assets["binding"], logger, args.fail_on_missing)
        context = enrich_context(context, row_count=len(records), sql_file=sql_path)

        rendered = render_report(assets["template_text"], context, logger=logger)
        out_path.write_text(rendered, encoding="utf-8")

        _write_preview(records, outdir)
        write_debug_outputs(outdir, context)

        used_placeholders = set(context.keys()) - {"report_meta"}
        all_placeholders = {x.get("placeholder") for x in assets["contract"].get("candidate_cells", [])}
        missing = sorted([p for p in all_placeholders if p and p not in used_placeholders])

        logger.dump(
            outdir / "render_log.json",
            query_executed=True,
            row_count=len(records),
            column_list=list(records[0].keys()) if records else [],
            binding_success_count=metrics["binding_success_count"],
            binding_warning_count=metrics["binding_warning_count"],
            missing_placeholders=missing,
            computed_placeholders=metrics["computed_count"],
        )

        if args.verbose:
            print(f"[OK] final report: {out_path}")
    except Exception as exc:
        logger.error("RUN_FAILED", str(exc))
        logger.dump(outdir / "render_log.json", query_executed=False)
        if args.error_html:
            write_error_html(out_path, str(exc))
        raise


if __name__ == "__main__":
    main()
