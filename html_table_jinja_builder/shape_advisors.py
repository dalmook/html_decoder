"""Shape advisor interfaces for rule-based/LLM-assisted expansion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseShapeAdvisor(ABC):
    """Interface for components that infer SQL-friendly shapes from template contracts."""

    @abstractmethod
    def advise(self, context: dict[str, Any]) -> dict[str, Any]:
        """Return shape/layout/binding recommendations."""


class RuleBasedShapeAdvisor(BaseShapeAdvisor):
    """Default stage-2 advisor using deterministic heuristics."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine

    def advise(self, context: dict[str, Any]) -> dict[str, Any]:
        return self.engine.run_rule_based(context)


class LLMShapeAdvisor(BaseShapeAdvisor):
    """Stub for future LLM integration. API call logic intentionally not implemented."""

    def advise(self, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            "LLMShapeAdvisor is a stage-4 extension point. "
            "Implement provider-specific API integration later."
        )
