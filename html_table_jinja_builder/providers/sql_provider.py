from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseSQLAdvisor(ABC):
    @abstractmethod
    def get_sql(self, sql_path: Path) -> str:
        pass


class ManualSQLProvider(BaseSQLAdvisor):
    def get_sql(self, sql_path: Path) -> str:
        return sql_path.read_text(encoding="utf-8")


class LLMSQLProvider(BaseSQLAdvisor):
    def get_sql(self, sql_path: Path) -> str:
        raise NotImplementedError("LLMSQLProvider is a stage-4 extension stub.")
