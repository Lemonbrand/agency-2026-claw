from __future__ import annotations

import json
from typing import Any

from . import paths
from .jsonio import append_jsonl, read_json, write_json
from .util import now_iso


def init_shared_runtime() -> dict[str, str]:
    paths.ensure_dirs()
    root = paths.judge_app_dir()
    (root / "locks").mkdir(parents=True, exist_ok=True)
    for name in ["frontend-requests.jsonl", "backend-events.jsonl"]:
        path = root / name
        if not path.exists():
            path.write_text("")
    handoff = root / "handoff.md"
    if not handoff.exists():
        handoff.write_text(
            "# Judge App Handoff\n\n"
            "Shared coordination space for frontend and backend agents.\n\n"
            "- Frontend requests: `frontend-requests.jsonl`\n"
            "- Backend events: `backend-events.jsonl`\n"
            "- Production contract: `app-manifest.json`\n"
        )
    return {
        "runtime": str(root),
        "frontend_requests": str(root / "frontend-requests.jsonl"),
        "backend_events": str(root / "backend-events.jsonl"),
        "manifest": str(root / "app-manifest.json"),
        "handoff": str(handoff),
    }


def backend_event(kind: str, payload: dict[str, Any]) -> None:
    init_shared_runtime()
    append_jsonl(
        paths.judge_app_dir() / "backend-events.jsonl",
        {"ts": now_iso(), "kind": kind, "payload": payload},
    )


def update_handoff(summary: dict[str, Any]) -> None:
    init_shared_runtime()
    lines = [
        "# Judge App Handoff",
        "",
        f"Updated: {now_iso()}",
        "",
        "## Backend Contract",
        "",
        f"- Manifest: `{summary.get('manifest_path', 'site/public/data/app-manifest.json')}`",
        f"- Challenges: `{summary.get('challenges_path', 'site/public/data/challenges.json')}`",
        f"- Q&A context: `{summary.get('qa_context_path', 'site/public/data/qa-context.json')}`",
        f"- Execution proof: `{summary.get('execution_proof_path', 'site/public/data/execution-proof.json')}`",
        "",
        "## Notes For Frontend",
        "",
        "- Read JSON from `site/public/data/*`; do not scrape `web/*.html`.",
        "- Treat iframe pages as proof artifacts, not source data.",
        "- Show proof-level chips from `challenges.json`.",
        "- Use `qa-context.json` for OpenRouter context assembly.",
    ]
    extra = summary.get("notes") or []
    if extra:
        lines.extend(["", "## Latest Notes", ""])
        lines.extend(f"- {note}" for note in extra)
    (paths.judge_app_dir() / "handoff.md").write_text("\n".join(lines) + "\n")


def write_manifest(manifest: dict[str, Any]) -> None:
    init_shared_runtime()
    write_json(paths.judge_app_dir() / "app-manifest.json", manifest)
    backend_event(
        "manifest_written",
        {
            "generated_at": manifest.get("generated_at"),
            "artifact_count": len(manifest.get("artifacts", [])),
        },
    )


def frontend_requests() -> list[dict[str, Any]]:
    path = paths.judge_app_dir() / "frontend-requests.jsonl"
    if not path.exists():
        return []
    requests = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        try:
            requests.append(json.loads(line))
        except Exception:
            continue
    return requests
