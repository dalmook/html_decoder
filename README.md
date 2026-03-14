# html_decoder

`html_table_jinja_builder`에 단계별 파이프라인이 구현되어 있습니다.

1. HTML 표 파싱 + 가상 좌표(A1) 계산
2. Jinja2 템플릿 / 데이터 계약 / mock 데이터 생성
3. 템플릿 요구 데이터 분석 + SQL shape(json) 추론
4. SQL 작성 가이드 문서(sql_prompt, skeleton, mapping guide) 생성
