from __future__ import annotations

import os
from pathlib import Path


def root() -> Path:
    return Path(os.environ.get("AGENCY_ROOT", Path.cwd())).resolve()


def data_dir() -> Path:
    return root() / "data"


def raw_dir() -> Path:
    return data_dir() / "raw"


def parquet_dir() -> Path:
    return data_dir() / "parquet"


def findings_dir() -> Path:
    return data_dir() / "findings"


def state_dir() -> Path:
    return root() / "state"


def web_dir() -> Path:
    return root() / "web"


def runtime_dir() -> Path:
    return root() / ".runtime"


def loop_audit_dir() -> Path:
    return runtime_dir() / "agency-loop-audit"


def judge_app_dir() -> Path:
    return runtime_dir() / "judge-app"


def site_public_dir() -> Path:
    return root() / "site" / "public"


def duckdb_path() -> Path:
    return data_dir() / "agency.duckdb"


def ensure_dirs() -> None:
    for path in [
        raw_dir(),
        parquet_dir(),
        findings_dir(),
        state_dir(),
        web_dir(),
        judge_app_dir(),
        site_public_dir() / "data",
        site_public_dir() / "briefs",
        site_public_dir() / "embeds",
        site_public_dir() / "charts",
    ]:
        path.mkdir(parents=True, exist_ok=True)
