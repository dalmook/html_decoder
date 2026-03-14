# html_table_jinja_builder

HTML 표 기반 리포트 자동화 파이프라인 (1~3단계).

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
### 실행(명시 인자)
```bash
python run_report.py --sql sql/user_query.sql --template output/template.html.j2 --contract output/data_contract.json --shape output/sql_shape.json --binding output/binding_spec.json --config config/report_config.json --out output/final_report.html
```

### 실행(설정 파일 기본값 사용)
```bash
python run_report.py --config config/report_config.json --out output/final_report.html
```

### DB 없이 mock-csv 모드(권장 개발/테스트)
```bash
python run_report.py --config config/report_config.json --mock-csv sample/mock_result.csv --out output/final_report.html --verbose
```

## Oracle 연결 설정
- `config/report_config.json` 의 `db` 섹션 설정
- 또는 환경변수 override
  - `ORACLE_HOST`, `ORACLE_PORT`, `ORACLE_SERVICE_NAME`, `ORACLE_USER`, `ORACLE_PASSWORD`, `ORACLE_CLIENT_LIB_DIR`

## 디버그 산출물
- `output/final_report.html`
- `output/final_context.json`
- `output/query_result_preview.csv`
- `output/query_result_preview.json`
- `output/render_log.json`

## 자주 나는 오류
- ORA-xxxx: DB 접속/권한/SQL 문법 확인
- lookup 실패: `binding_spec.json`의 row_keys/value_column 과 SQL 결과 컬럼 정합성 확인
- 컬럼명 mismatch: `runtime.case_insensitive_columns=true` 사용 또는 SQL alias 맞추기
- binding 누락: `render_log.json` 의 `missing_placeholders` 확인

## 확장 포인트
- SQL 공급자 인터페이스: `BaseSQLAdvisor`, `ManualSQLProvider`, `LLMSQLProvider(stub)`
- 4단계: LLM 기반 SQL 초안 자동 생성기로 확장
