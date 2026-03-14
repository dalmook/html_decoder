WITH base AS (
    SELECT
        PERIOD,
        BUSINESS_UNIT,
        PRODUCT_GROUP,
        SALES,
        OPERATING_PROFIT,
        MARGIN_PCT
    FROM your_source_table
)
SELECT
    PERIOD,
        BUSINESS_UNIT,
        PRODUCT_GROUP,
        SALES,
        OPERATING_PROFIT,
        MARGIN_PCT
FROM base
