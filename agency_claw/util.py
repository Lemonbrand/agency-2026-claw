from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip()).strip("_").lower()
    return cleaned or "unnamed"


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def first_match(columns: Iterable[str], candidates: list[str]) -> str | None:
    cols = list(columns)
    lower = {c.lower(): c for c in cols}
    for candidate in candidates:
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    for candidate in candidates:
        needle = candidate.lower()
        for col in cols:
            if needle in col.lower():
                return col
    return None


def now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
