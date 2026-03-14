from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def maybe_run_preview(
    cfg: dict[str, Any],
    auto_preview: bool,
    allow_db_execution: bool,
    mock_csv: str | None,
    generated_sql_path: Path,
    verbose: bool,
) -> dict[str, Any]:
    preview_cfg = cfg.get("preview", {})
    if not auto_preview:
        return {"executed": False, "reason": "auto_preview flag disabled"}
    if not preview_cfg.get("enabled", False):
        return {"executed": False, "reason": "preview.enabled is false in config"}

    cmd = [
        "python",
        "run_report.py",
        "--sql",
        str(generated_sql_path),
        "--config",
        "config/report_config.json",
        "--out",
        "output/generated_sql_preview.html",
    ]

    if mock_csv:
        cmd.extend(["--mock-csv", mock_csv])
    else:
        if not allow_db_execution or not preview_cfg.get("allow_db_execution", False):
            return {"executed": False, "reason": "DB execution is blocked (need --allow-db-execution and preview.allow_db_execution=true)"}

    if verbose:
        cmd.append("--verbose")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "executed": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-2000:],
        "stderr": proc.stderr[-2000:],
    }


def copy_preview_context(outdir: Path) -> None:
    src = outdir / "final_context.json"
    dst = outdir / "generated_sql_preview_context.json"
    if src.exists():
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")


def write_generation_outputs(
    out_sql: Path,
    out_explained: Path,
    out_log: Path,
    out_checklist: Path,
    out_prompt: Path,
    sql_text: str,
    explained_md: str,
    checklist_md: str,
    prompt_text: str,
    log_payload: dict[str, Any],
) -> None:
    out_sql.write_text(sql_text, encoding="utf-8")
    out_explained.write_text(explained_md, encoding="utf-8")
    out_checklist.write_text(checklist_md, encoding="utf-8")
    out_prompt.write_text(prompt_text, encoding="utf-8")
    out_log.write_text(json.dumps(log_payload, ensure_ascii=False, indent=2), encoding="utf-8")
