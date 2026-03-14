from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_optional(path: Path | None) -> str:
    if not path:
        return ""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_generation_assets(
    template_path: Path,
    contract_path: Path,
    shape_path: Path,
    binding_path: Path,
    schema_notes: Path | None,
    business_rules: Path | None,
    examples_dir: Path | None,
) -> dict[str, Any]:
    def load_json(p: Path) -> dict[str, Any]:
        return json.loads(p.read_text(encoding="utf-8"))

    examples = []
    if examples_dir and examples_dir.exists():
        for fp in sorted(examples_dir.glob("*.sql")):
            examples.append({"name": fp.name, "sql": fp.read_text(encoding="utf-8")})

    return {
        "template": template_path.read_text(encoding="utf-8"),
        "contract": load_json(contract_path),
        "shape": load_json(shape_path),
        "binding": load_json(binding_path),
        "schema_notes": _read_optional(schema_notes),
        "business_rules": _read_optional(business_rules),
        "examples": examples,
    }


def build_generation_prompt(assets: dict[str, Any], llm_cfg: dict[str, Any], strict_json: bool = False) -> str:
    shape = assets["shape"]
    generation_cfg = llm_cfg.get("generation", {})
    target_shape = generation_cfg.get("target_shape", "wide")

    example_sql_block = "\n\n".join(
        [f"-- example: {x['name']}\n{x['sql'][:1200]}" for x in assets["examples"][:3]]
    )

    json_rule = (
        "반드시 유효한 JSON 객체만 출력하고, 설명 문장/markdown fence를 절대 추가하지 마라."
        if strict_json
        else "가능하면 JSON 형식을 엄수하라."
    )

    prompt = f"""
당신의 역할: Oracle SQL 초안 생성 조력자.
이 SQL은 '초안'이며 사용자가 최종 검토한다.

요구사항:
1) Oracle SQL
2) SELECT/CTE ONLY (INSERT/UPDATE/DELETE/MERGE/DDL 금지)
3) 숫자 포맷(to_char 등) 최소화, raw numeric 반환
4) NULL 처리 고려
5) 템플릿 렌더링용 placeholder 매핑 고려
6) target shape: {target_shape}
7) {json_rule}

템플릿 요약(일부):
{assets['template'][:1500]}

sql_shape.json:
{json.dumps(shape, ensure_ascii=False, indent=2)[:6000]}

binding_spec.json:
{json.dumps(assets['binding'], ensure_ascii=False, indent=2)[:6000]}

schema_notes.md:
{assets['schema_notes'][:3000] if assets['schema_notes'] else '(없음)'}

business_rules.md:
{assets['business_rules'][:3000] if assets['business_rules'] else '(없음)'}

example_sql count: {len(assets['examples'])}
{example_sql_block if example_sql_block else '(예시 없음)'}

반환 형식(JSON):
{{
  "sql": "...",
  "assumptions": ["..."],
  "expected_output_shape": {{
    "grain_keys": ["..."],
    "dimension_columns": ["..."],
    "measure_columns": ["..."]
  }},
  "binding_notes": [
    {{"placeholder":"cell_D5","mapping":"..."}}
  ],
  "risks": ["..."]
}}
""".strip()
    return prompt
