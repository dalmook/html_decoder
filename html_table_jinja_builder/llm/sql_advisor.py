from __future__ import annotations

from typing import Any

from llm.base_provider import BaseLLMProvider


class SQLGenerationAdvisor:
    def __init__(self, provider: BaseLLMProvider) -> None:
        self.provider = provider

    def call_llm(self, prompt: str) -> str:
        return self.provider.generate(prompt)


def build_fallback_sql(shape: dict[str, Any]) -> str:
    wide = shape.get("recommended_shape_wide", {})
    dims = wide.get("dimension_columns", ["PERIOD", "BUSINESS_UNIT", "PRODUCT_GROUP"])
    measures = wide.get("measure_columns", ["SALES", "OPERATING_PROFIT", "MARGIN_PCT"])
    cols = dims + measures
    select_cols = ",\n        ".join(cols)
    return f"""WITH base AS (
    SELECT
        {select_cols}
    FROM your_source_table
)
SELECT
    {select_cols}
FROM base"""


def build_default_response(shape: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "sql": build_fallback_sql(shape),
        "assumptions": [f"LLM call unavailable: {reason}", "fallback skeleton generated"],
        "expected_output_shape": {
            "grain_keys": shape.get("recommended_shape_wide", {}).get("grain_keys", []),
            "dimension_columns": shape.get("recommended_shape_wide", {}).get("dimension_columns", []),
            "measure_columns": shape.get("recommended_shape_wide", {}).get("measure_columns", []),
        },
        "binding_notes": [],
        "risks": ["Manual SQL completion required"],
    }
