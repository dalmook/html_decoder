# SQL 작성 프롬프트

## 템플릿이 요구하는 최종 데이터 구조
- 템플릿명: `template.html.j2`
- 권장 레이아웃: 기간방향 `mixed`, 측정치방향 `vertical`
- Placeholder 개수: 24

## 권장 Wide Shape
- Grain: PERIOD, BUSINESS_UNIT, PRODUCT_GROUP
- Dimension 컬럼: PERIOD, BUSINESS_UNIT, PRODUCT_GROUP
- Measure 컬럼: SALES, OPERATING_PROFIT, MARGIN_PCT

## 권장 Long Shape
- Grain: PERIOD, BUSINESS_UNIT, PRODUCT_GROUP, MEASURE
- Pivot key: MEASURE
- Value 컬럼: VALUE

## 기간 컬럼 후보
- WORKDATE, WEEK_CD, QUARTER, YM

## 주의사항
- NULL 처리(NVL/COALESCE) 적용
- 숫자/소수점/천단위 포맷은 Python/Jinja에서 처리 권장
- SQL은 raw numeric 반환 권장
- 최신주/TTL/전주대비 같은 파생값은 SQL 또는 Python 후처리 가능

## 예시 결과 행
```json
[
  {
    "PERIOD": "2026Q1",
    "BUSINESS_UNIT": "DRAM",
    "PRODUCT_GROUP": "Server",
    "SALES": 1250,
    "OPERATING_PROFIT": 210,
    "MARGIN_PCT": 16.8
  }
]
```