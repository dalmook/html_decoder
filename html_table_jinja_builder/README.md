# html_table_jinja_builder

HTML 표 기반 리포트 자동화 파이프라인 (1~4단계).

## 1단계: HTML 표 → 템플릿/계약/mock
```bash
python build_template.py --input input/sample_table.html --output-dir output
python render_demo.py --template output/template.html.j2 --data output/mock_data.json --out output/rendered_preview.html
```

## 2단계: SQL shape 추론 + SQL 가이드 생성
```bash
python infer_sql_shape.py --template output/template.html.j2 --contract output/data_contract.json --outdir output
python make_sql_docs.py --shape output/sql_shape.json --contract output/data_contract.json --outdir output
```

## 3단계: 사용자 SQL 실행 + 바인딩 + 최종 HTML 생성
```bash
python run_report.py --config config/report_config.json --mock-csv sample/mock_result.csv --out output/final_report.html --verbose
```

## 4단계: LLM 기반 SQL 초안 자동 생성
### 환경변수 (Windows CMD)
```cmd
set LLM_API_KEY=YOUR_REAL_KEY
```

### 기본 실행
```bash
python generate_sql.py --llm-config config/llm_config.json --out-sql output/generated_sql.sql --verbose
```

### 부가 문서 입력
```bash
python generate_sql.py --llm-config config/llm_config.json --schema-notes input/schema_notes.md --business-rules input/business_rules.md --examples-dir input/example_sql --out-sql output/generated_sql.sql
```

### 자동 preview (기본은 차단)
```bash
python generate_sql.py --auto-preview --mock-csv sample/mock_result.csv
python generate_sql.py --auto-preview --allow-db-execution
```

> `--auto-preview`만으로는 DB 실행되지 않습니다. 반드시
> 1) `--allow-db-execution` 옵션 +
> 2) `config/llm_config.json`의 `preview.allow_db_execution=true`
> 두 조건을 모두 만족해야 DB preview 실행됩니다.

## 4단계 산출물
- `output/generated_sql.sql`
- `output/generated_sql_explained.md`
- `output/sql_generation_log.json`
- `output/sql_review_checklist.md`
- `output/sql_prompt_debug.txt`
- optional: `output/generated_sql_preview.html`
- optional: `output/generated_sql_preview_context.json`

## 안전정책
- API KEY는 반드시 환경변수에서만 로딩
- 생성 SQL은 SELECT/CTE only 정적 검증 수행
- DML/DDL 위험 키워드 탐지 시 validator fail
- DB 자동 실행 기본 비활성
- 로그에는 API key mask 처리

## 자주 나는 오류
- JSON 파싱 실패: LLM 응답 형식이 어긋남(자동 fallback SQL 추출 시도)
- validator 실패: DML/다중 statement/measure 컬럼 누락 점검
- placeholder 매핑 불일치: binding_spec.json과 SQL alias 정합성 확인
- preview 차단: `--auto-preview`만 사용했고 DB 허용 플래그가 없는 경우

## 흐름 정리
1) HTML 표 입력
2) 템플릿/contract 생성
3) SQL shape 추론
4) 사용자 SQL 직접 작성 또는 LLM SQL 초안 생성
5) run_report.py로 최종 HTML 렌더링
