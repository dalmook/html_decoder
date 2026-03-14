from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing JSON file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_sql_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing SQL file: {path}")
    return path.read_text(encoding="utf-8")


def load_template_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Missing template file: {path}")
    return path.read_text(encoding="utf-8")


def load_report_assets(template: Path, contract: Path, shape: Path, binding: Path) -> dict[str, Any]:
    return {
        "template_text": load_template_text(template),
        "contract": load_json(contract),
        "shape": load_json(shape),
        "binding": load_json(binding),
    }


def merge_env_overrides(config: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    db = config.setdefault("db", {})
    mapping = {
        "ORACLE_HOST": "host",
        "ORACLE_PORT": "port",
        "ORACLE_SERVICE_NAME": "service_name",
        "ORACLE_USER": "user",
        "ORACLE_PASSWORD": "password",
        "ORACLE_CLIENT_LIB_DIR": "client_lib_dir",
    }
    for env_key, db_key in mapping.items():
        if env.get(env_key):
            db[db_key] = env[env_key]
    return config
