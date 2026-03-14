# html_decoder

`html_table_jinja_builder`에 1~3단계 파이프라인이 구현되어 있습니다.

1. HTML 표 → template/data_contract/mock
2. template/data_contract → sql_shape/binding/docs
3. 사용자 SQL(or mock CSV) + binding_spec → final_report.html
