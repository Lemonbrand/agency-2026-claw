from __future__ import annotations

from typing import Any

from . import paths
from .jsonio import append_jsonl, read_json, write_json
from .util import now_iso


def event(kind: str, payload: dict[str, Any]) -> None:
    append_jsonl(
        paths.state_dir() / "events.jsonl",
        {"ts": now_iso(), "kind": kind, "payload": payload},
    )


def findings_path(skill: str) -> str:
    return str(paths.findings_dir() / f"{skill}.json")


def save_findings(skill: str, findings: list[dict[str, Any]]) -> None:
    out = {
        "skill": skill,
        "generated_at": now_iso(),
        "count": len(findings),
        "findings": findings,
    }
    write_json(paths.findings_dir() / f"{skill}.json", out)
    event("findings_saved", {"skill": skill, "count": len(findings)})


def load_all_findings() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in sorted(paths.findings_dir().glob("*.json")):
        if path.name in {"correlated.json", "verified.json", "neotoma-payload.json"}:
            continue
        data = read_json(path, {})
        out.extend(data.get("findings", []))
    return out
