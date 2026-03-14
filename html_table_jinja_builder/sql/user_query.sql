-- 사용자 수정용 SQL 샘플 (Oracle)
-- 아래 컬럼 alias는 output/binding_spec.json 의 value_column/row_keys 와 맞춰주세요.
WITH source_data AS (
    SELECT 'DRAM' AS BUSINESS_UNIT, 'Server' AS PRODUCT_GROUP, 1250 AS "매출", 210 AS "영업이익", 16.8 AS "마진율" FROM dual
    UNION ALL
    SELECT 'DRAM', 'Mobile', 980, 145, 14.8 FROM dual
    UNION ALL
    SELECT 'FLASH', 'Client SSD', -120, -35, -29.2 FROM dual
    UNION ALL
    SELECT '합계', '합계', 2110, 320, 15.2 FROM dual
)
SELECT *
FROM source_data;
