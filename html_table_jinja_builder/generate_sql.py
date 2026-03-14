from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from core.sql_postprocess import postprocess_sql
from core.sql_preview_runner import copy_preview_context, maybe_run_preview, write_generation_outputs
from core.sql_validator import validate_sql_text
from llm.http_provider import HttpLLMProvider
from llm.prompt_builder import build_generation_prompt, load_generation_assets
from llm.response_parser import parse_generation_response
from llm.self_reviewer import SQLSelfReviewer
from llm.sql_advisor import SQLGenerationAdvisor, build_default_response


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default(cli: str | None, fallback: str) -> Path:
    return Path(cli) if cli else Path(fallback)


def _mask(text: str) -> str:
    if not text:
        return text
    if len(text) <= 6:
        return "***"
    return text[:3] + "***" + text[-2:]


def _build_explained_md(result: dict[str, Any], llm_cfg: dict[str, Any], validator: dict[str, Any], review: dict[str, Any]) -> str:
    provider = llm_cfg.get("provider", {})
    shape = result.get("expected_output_shape", {})
    assumptions = result.get("assumptions", [])
    risks = result.get("risks", [])
    binding_notes = result.get("binding_notes", [])

    lines = [
        "# Generated SQL Explained",
        "",
        f"- 생성 시각: {datetime.utcnow().isoformat()}Z",
        f"- 사용 모델: {provider.get('model', '(unknown)')}",
        "- 목적: 템플릿/바인딩 요구를 만족하는 Oracle SQL **초안** 생성",
        "- 중요: 이 SQL은 자동 생성된 초안이며, 실제 테이블/컬럼/비즈니스 룰은 반드시 사용자 검토가 필요함",
        "",
        "## LLM 가정 사항",
    ]
    lines.extend([f"- {x}" for x in assumptions] or ["- (없음)"])
    lines.extend([
        "",
        "## 기대 결과 Shape",
        f"- grain_keys: {shape.get('grain_keys', [])}",
        f"- dimension_columns: {shape.get('dimension_columns', [])}",
        f"- measure_columns: {shape.get('measure_columns', [])}",
        "",
        "## Placeholder 매핑 핵심",
    ])
    for item in binding_notes[:20]:
        lines.append(f"- {item.get('placeholder')}: {item.get('mapping')}")
    if not binding_notes:
        lines.append("- (없음)")

    lines.extend([
        "",
        "## Validator 결과",
        f"- valid: {validator.get('valid')}",
    ])
    for issue in validator.get("issues", []):
        lines.append(f"- issue: {issue}")

    lines.extend([
        "",
        "## Self Review",
        f"- status: {review.get('status')}",
    ])
    for n in review.get("notes", []):
        lines.append(f"- {n}")

    lines.extend([
        "",
        "## 리스크/검토 필요",
    ])
    lines.extend([f"- {r}" for r in risks] or ["- (없음)"])
    return "\n".join(lines) + "\n"


def _build_review_checklist() -> str:
    items = [
        "실제 테이블명/스키마명이 맞는가?",
        "SELECT 대상 컬럼 alias가 binding_spec와 일치하는가?",
        "기간 조건(주/월/분기)이 보고서 기준과 일치하는가?",
        "DRAM/FLASH 등 필터 의도가 맞는가?",
        "TTL/전주대비/파생지표 계산식이 정확한가?",
        "SQL에서 과도한 포맷(to_char) 없이 raw numeric을 반환하는가?",
        "run_report.py 바인딩 lookup(row_keys/value_column)과 충돌 없는가?",
        "단일 SELECT/CTE 문인지(다중 statement 아님) 확인했는가?",
    ]
    out = ["# SQL Review Checklist", ""]
    out.extend([f"- [ ] {x}" for x in items])
    return "\n".join(out) + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate SQL draft using LLM from template/contract/shape/binding")
    p.add_argument("--template")
    p.add_argument("--contract")
    p.add_argument("--shape")
    p.add_argument("--binding")
    p.add_argument("--llm-config", default="config/llm_config.json")
    p.add_argument("--schema-notes")
    p.add_argument("--business-rules")
    p.add_argument("--examples-dir")
    p.add_argument("--out-sql", default="output/generated_sql.sql")
    p.add_argument("--auto-preview", action="store_true")
    p.add_argument("--allow-db-execution", action="store_true")
    p.add_argument("--mock-csv")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    llm_cfg = _load_json(Path(args.llm_config))

    template_path = _default(args.template, "output/template.html.j2")
    contract_path = _default(args.contract, "output/data_contract.json")
    shape_path = _default(args.shape, "output/sql_shape.json")
    binding_path = _default(args.binding, "output/binding_spec.json")

    schema_notes = Path(args.schema_notes) if args.schema_notes else Path("input/schema_notes.md")
    business_rules = Path(args.business_rules) if args.business_rules else Path("input/business_rules.md")
    examples_dir = Path(args.examples_dir) if args.examples_dir else Path("input/example_sql")

    assets = load_generation_assets(
        template_path,
        contract_path,
        shape_path,
        binding_path,
        schema_notes if schema_notes.exists() else None,
        business_rules if business_rules.exists() else None,
        examples_dir if examples_dir.exists() else None,
    )

    out_sql = Path(args.out_sql)
    outdir = out_sql.parent
    outdir.mkdir(parents=True, exist_ok=True)

    prompt = build_generation_prompt(assets, llm_cfg, strict_json=False)
    reviewer = SQLSelfReviewer()

    max_retry = int(llm_cfg.get("generation", {}).get("max_retry", 2))
    attempts = []
    parsed: dict[str, Any] | None = None
    fallback_used = False

    for attempt in range(1, max_retry + 1):
        strict = attempt >= 2
        prompt_used = build_generation_prompt(assets, llm_cfg, strict_json=strict)
        call_error = None
        raw_resp = ""
        try:
            provider = HttpLLMProvider(llm_cfg.get("provider", {}))
            advisor = SQLGenerationAdvisor(provider)
            raw_resp = advisor.call_llm(prompt_used)
            parsed_obj, fallback_flag = parse_generation_response(raw_resp)
            parsed = parsed_obj
            fallback_used = fallback_flag
        except Exception as exc:
            call_error = str(exc)
            parsed = build_default_response(assets["shape"], reason=call_error)
            fallback_used = True

        sql_text = postprocess_sql(parsed.get("sql", ""))
        validator = validate_sql_text(sql_text, assets["shape"], llm_cfg.get("generation", {}))
        review = reviewer.review_sql_draft(sql_text, assets["shape"], llm_cfg)
        attempts.append(
            {
                "attempt": attempt,
                "strict_json_prompt": strict,
                "llm_call_error": call_error,
                "fallback_used": fallback_used,
                "validator": validator,
                "review": review,
            }
        )

        if validator.get("valid"):
            break

        # if invalid, keep retrying with strict prompt
        parsed = {
            **parsed,
            "assumptions": parsed.get("assumptions", []) + ["validator failed; retry requested"],
        }

    assert parsed is not None
    sql_text = postprocess_sql(parsed.get("sql", ""))
    validator = validate_sql_text(sql_text, assets["shape"], llm_cfg.get("generation", {}))
    review = reviewer.review_sql_draft(sql_text, assets["shape"], llm_cfg)

    explained = _build_explained_md(parsed, llm_cfg, validator, review)
    checklist = _build_review_checklist()

    preview_result = maybe_run_preview(
        llm_cfg,
        auto_preview=args.auto_preview,
        allow_db_execution=args.allow_db_execution,
        mock_csv=args.mock_csv,
        generated_sql_path=out_sql,
        verbose=args.verbose,
    )

    if preview_result.get("executed"):
        copy_preview_context(outdir)

    log_payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "provider": {
            "type": llm_cfg.get("provider", {}).get("type"),
            "base_url": llm_cfg.get("provider", {}).get("base_url"),
            "api_key_env": llm_cfg.get("provider", {}).get("api_key_env"),
            "api_key_masked": _mask(os.getenv(llm_cfg.get("provider", {}).get("api_key_env", "LLM_API_KEY"), "")),
            "model": llm_cfg.get("provider", {}).get("model"),
        },
        "inputs": {
            "template": str(template_path),
            "contract": str(contract_path),
            "shape": str(shape_path),
            "binding": str(binding_path),
            "schema_notes": str(schema_notes) if schema_notes.exists() else None,
            "business_rules": str(business_rules) if business_rules.exists() else None,
            "examples_used": [x.get("name") for x in assets.get("examples", [])],
        },
        "fallback_used": fallback_used,
        "response_parse_mode": "fallback" if fallback_used else "json",
        "attempts": attempts,
        "final_validator": validator,
        "final_review": review,
        "preview": preview_result,
    }

    write_generation_outputs(
        out_sql=out_sql,
        out_explained=outdir / "generated_sql_explained.md",
        out_log=outdir / "sql_generation_log.json",
        out_checklist=outdir / "sql_review_checklist.md",
        out_prompt=outdir / "sql_prompt_debug.txt",
        sql_text=sql_text,
        explained_md=explained,
        checklist_md=checklist,
        prompt_text=prompt,
        log_payload=log_payload,
    )

    if args.verbose:
        print(f"[OK] generated SQL: {out_sql}")
        print(f"[OK] validator valid: {validator.get('valid')}")
        print(f"[OK] preview: {preview_result}")


if __name__ == "__main__":
    main()
