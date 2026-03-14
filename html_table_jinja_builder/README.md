# html_table_jinja_builder

PowerPoint/Excel에서 복붙한 HTML 표를 입력받아 템플릿/계약 생성(1단계)과 SQL shape 설계 문서화(2단계)까지 수행하는 도구입니다.

## 1단계: HTML 표 → 템플릿/계약/mock

산출물
- `output/template.html.j2`
- `output/data_contract.json`
- `output/mock_data.json`
- `output/rendered_preview.html`

실행
```bash
python build_template.py --input input/sample_table.html --output-dir output
python render_demo.py --template output/template.html.j2 --data output/mock_data.json --out output/rendered_preview.html
```

## 2단계: 템플릿 요구 구조 분석 → SQL shape/가이드 생성

입력
- `output/template.html.j2`
- `output/data_contract.json`
- `output/mock_data.json`

산출물
- `output/sql_shape.json`
- `output/binding_spec.json`
- `output/sql_prompt.md`
- `output/sql_skeleton.sql`
- `output/mapping_guide.md`

실행
```bash
python infer_sql_shape.py --template output/template.html.j2 --contract output/data_contract.json --outdir output
python make_sql_docs.py --shape output/sql_shape.json --contract output/data_contract.json --outdir output
```

추론 포인트(규칙 기반)
- period 패턴(quarter/week/month)
- total/ttl 패턴
- measure-like 텍스트(판매/재고/risk/wip 등)
- computed 후보(비율/%/증감 등)

## 확장 구조

향후 LLM 연동을 위해 인터페이스를 분리했습니다.
- `BaseShapeAdvisor`
- `RuleBasedShapeAdvisor`
- `LLMShapeAdvisor`(stub)

## 다음 단계 예고

- 3단계: 사용자가 작성한 SQL을 입력하면 실제 렌더링까지 수행하는 독립 실행기
- 4단계: LLM API 기반 SQL 초안 자동 생성기
