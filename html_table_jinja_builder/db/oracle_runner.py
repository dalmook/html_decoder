from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def _read_mock_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def execute_query(sql_text: str, db_cfg: dict[str, Any], mock_csv: str | None = None) -> list[dict[str, Any]]:
    if mock_csv:
        return _read_mock_csv(Path(mock_csv))

    try:
        import oracledb  # type: ignore
    except Exception as exc:
        raise RuntimeError("python-oracledb is not installed. Use --mock-csv or install dependency.") from exc

    client_lib_dir = db_cfg.get("client_lib_dir")
    if client_lib_dir:
        oracledb.init_oracle_client(lib_dir=client_lib_dir)

    dsn = oracledb.makedsn(
        db_cfg.get("host"),
        int(db_cfg.get("port", 1521)),
        service_name=db_cfg.get("service_name"),
    )
    conn = oracledb.connect(
        user=db_cfg.get("user"),
        password=db_cfg.get("password"),
        dsn=dsn,
        encoding=db_cfg.get("encoding", "UTF-8"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql_text)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]
    finally:
        conn.close()
