from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import paths
from .util import now_iso


FORBIDDEN_SQL = (
    "insert",
    "update",
    "delete",
    "drop",
    "create",
    "alter",
    "copy",
    "truncate",
    "attach",
    "detach",
    "install",
    "load",
    "call",
    "pragma",
)

TABLE_RE = re.compile(r"\b(?:pg\.)?(cra|fed|ab|general)\.([A-Za-z_][A-Za-z0-9_]*)\b")


class DirectDBError(RuntimeError):
    pass


def load_env_value(key: str) -> str | None:
    if os.environ.get(key):
        return os.environ[key]
    env_path = paths.root() / ".env"
    if not env_path.exists():
        return None
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, value = stripped.split("=", 1)
        if name == key:
            return value.strip().strip("'").strip('"')
    return None


def pg_url() -> str:
    value = load_env_value("HACKATHON_PG")
    if not value:
        raise DirectDBError("HACKATHON_PG is not set")
    return value


def sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.strip().encode("utf-8")).hexdigest()


def referenced_tables(sql: str) -> list[str]:
    return sorted({f"{schema}.{table}" for schema, table in TABLE_RE.findall(sql)})


def safe_sql(sql: str) -> str:
    stripped = sql.strip().rstrip(";")
    lowered = re.sub(r"\s+", " ", stripped.lower())
    if not (lowered.startswith("select ") or lowered.startswith("with ")):
        raise DirectDBError("Only SELECT/WITH SQL is allowed")
    padded = f" {lowered} "
    for token in FORBIDDEN_SQL:
        if re.search(rf"\b{re.escape(token)}\b", padded):
            raise DirectDBError(f"Forbidden SQL token: {token}")
    return stripped


def psql_command() -> tuple[list[str], dict[str, str]]:
    parsed = urlparse(pg_url())
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise DirectDBError("HACKATHON_PG must be a Postgres URL")
    dbname = parsed.path.lstrip("/")
    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password
    cmd = [
        "psql",
        "-X",
        "-q",
        "-t",
        "-A",
        "-h",
        parsed.hostname or "",
        "-p",
        str(parsed.port or 5432),
        "-U",
        parsed.username or "",
        "-d",
        dbname,
    ]
    return cmd, env


def postgres_sql(sql: str, *, max_rows: int, timeout_s: int) -> str:
    timeout_ms = max(1, int(timeout_s * 1000))
    return f"""
SET statement_timeout = {timeout_ms};
WITH __lc_rows AS (
  SELECT * FROM (
{sql}
  ) AS __lc_inner
  LIMIT {max_rows + 1}
)
SELECT COALESCE(json_agg(row_to_json(__lc_rows)), '[]'::json)::text
FROM __lc_rows;
""".strip()


def query(sql: str, *, max_rows: int = 25, timeout_s: int = 60) -> dict[str, Any]:
    safe = safe_sql(sql)
    started = time.time()
    tables = referenced_tables(safe)
    pg_sql = postgres_sql(safe.replace("pg.", ""), max_rows=max_rows, timeout_s=timeout_s)
    cmd, env = psql_command()
    try:
        result = subprocess.run(
            [*cmd, "-c", pg_sql],
            cwd=str(paths.root()),
            env=env,
            text=True,
            capture_output=True,
            timeout=timeout_s + 2,
            check=False,
        )
        if result.returncode != 0:
            raise DirectDBError((result.stderr or result.stdout).strip())
        rows = json.loads(result.stdout.strip() or "[]")
        truncated = len(rows) > max_rows
        rows = rows[:max_rows]
        elapsed_ms = int((time.time() - started) * 1000)
        return {
            "ok": True,
            "checked_at": now_iso(),
            "sql_hash": sql_hash(safe),
            "sql": safe,
            "tables": tables,
            "elapsed_ms": elapsed_ms,
            "rows_returned": len(rows),
            "truncated": truncated,
            "rows": rows,
        }
    except Exception as exc:
        elapsed_ms = int((time.time() - started) * 1000)
        return {
            "ok": False,
            "checked_at": now_iso(),
            "sql_hash": sql_hash(safe),
            "sql": safe,
            "tables": tables,
            "elapsed_ms": elapsed_ms,
            "error": str(exc),
            "rows_returned": 0,
            "rows": [],
        }


def write_sql_artifact(path: Path, sql: str) -> dict[str, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe = safe_sql(sql)
    path.write_text(safe + "\n")
    return {"path": str(path.relative_to(paths.root())), "sha256": sql_hash(safe)}
