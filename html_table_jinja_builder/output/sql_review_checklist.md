# SQL Review Checklist

- [ ] 실제 테이블명/스키마명이 맞는가?
- [ ] SELECT 대상 컬럼 alias가 binding_spec와 일치하는가?
- [ ] 기간 조건(주/월/분기)이 보고서 기준과 일치하는가?
- [ ] DRAM/FLASH 등 필터 의도가 맞는가?
- [ ] TTL/전주대비/파생지표 계산식이 정확한가?
- [ ] SQL에서 과도한 포맷(to_char) 없이 raw numeric을 반환하는가?
- [ ] run_report.py 바인딩 lookup(row_keys/value_column)과 충돌 없는가?
- [ ] 단일 SELECT/CTE 문인지(다중 statement 아님) 확인했는가?
