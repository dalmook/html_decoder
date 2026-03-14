from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Return raw model response text."""
