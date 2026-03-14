from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RenderLogger:
    entries: list[dict[str, Any]] = field(default_factory=list)

    def info(self, code: str, message: str, **extra: Any) -> None:
        self.entries.append({"level": "info", "code": code, "message": message, **extra})

    def warning(self, code: str, message: str, **extra: Any) -> None:
        self.entries.append({"level": "warning", "code": code, "message": message, **extra})

    def error(self, code: str, message: str, **extra: Any) -> None:
        self.entries.append({"level": "error", "code": code, "message": message, **extra})

    def dump(self, path: Path, **summary: Any) -> None:
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "summary": summary,
            "entries": self.entries,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
