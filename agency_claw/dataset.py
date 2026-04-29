from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from . import paths
from .duck import records
from .jsonio import write_json
from .util import quote_ident, sha256_file, slug


SUPPORTED = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".parquet"}


def connect() -> duckdb.DuckDBPyConnection:
    paths.ensure_dirs()
    return duckdb.connect(str(paths.duckdb_path()))


def discover_files() -> list[Path]:
    return sorted(
        path
        for path in paths.raw_dir().iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED
    )


def load_file(con: duckdb.DuckDBPyConnection, path: Path) -> dict[str, Any]:
    table = slug(path.stem)
    quoted = quote_ident(table)
    suffix = path.suffix.lower()

    if suffix in {".csv", ".tsv"}:
        delim = "\t" if suffix == ".tsv" else ","
        sql = f"CREATE OR REPLACE TABLE {quoted} AS SELECT * FROM read_csv_auto(?, delim=?, ignore_errors=true)"
        con.execute(sql, [str(path), delim])
    elif suffix in {".json", ".jsonl", ".ndjson"}:
        con.execute(
            f"CREATE OR REPLACE TABLE {quoted} AS SELECT * FROM read_json_auto(?)",
            [str(path)],
        )
    elif suffix == ".parquet":
        con.execute(
            f"CREATE OR REPLACE TABLE {quoted} AS SELECT * FROM read_parquet(?)",
            [str(path)],
        )
    else:
        raise ValueError(f"unsupported file type: {path.name}")

    parquet_path = paths.parquet_dir() / f"{table}.parquet"
    con.execute(f"COPY {quoted} TO ? (FORMAT PARQUET)", [str(parquet_path)])

    return {
        "table": table,
        "source_path": str(path),
        "source_name": path.name,
        "source_sha256": sha256_file(path),
        "parquet_path": str(parquet_path),
        "source_bytes": path.stat().st_size,
    }


def profile_table(con: duckdb.DuckDBPyConnection, table: str) -> dict[str, Any]:
    quoted = quote_ident(table)
    info = con.execute(f"PRAGMA table_info({quoted})").fetchall()
    columns = [{"name": row[1], "type": row[2]} for row in info]
    row_count = con.execute(f"SELECT count(*) FROM {quoted}").fetchone()[0]
    sample = records(con, f"SELECT * FROM {quoted} LIMIT 5")

    nulls: dict[str, int] = {}
    for column in columns:
        name = column["name"]
        nulls[name] = con.execute(
            f"SELECT count(*) FROM {quoted} WHERE {quote_ident(name)} IS NULL"
        ).fetchone()[0]

    return {
        "table": table,
        "row_count": row_count,
        "columns": columns,
        "nulls": nulls,
        "sample": json.loads(json.dumps(sample, default=str)),
    }


def onboard() -> dict[str, Any]:
    paths.ensure_dirs()
    files = discover_files()
    con = connect()
    manifest = [load_file(con, path) for path in files]
    profiles = [profile_table(con, row["table"]) for row in manifest]
    out = {"manifest": manifest, "profiles": profiles}
    write_json(paths.state_dir() / "dataset-manifest.json", manifest)
    write_json(paths.state_dir() / "discovered.schema.json", profiles)
    return out


def table_profiles() -> list[dict[str, Any]]:
    data = paths.state_dir() / "discovered.schema.json"
    if not data.exists():
        return []
    return json.loads(data.read_text())
