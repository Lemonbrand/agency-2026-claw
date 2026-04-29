from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from . import paths
from .challenge_contract import CHALLENGES, Challenge
from .directdb import sql_hash
from .jsonio import read_json
from .util import now_iso


STATUS_RE = re.compile(r"^Current executable status:\s*(.+)$", re.MULTILINE)
PRESENTATION_RE = re.compile(r"^Presentation sentence:\s*(.+)$", re.MULTILINE)
SQL_BLOCK_RE = re.compile(r"```sql\s+(.*?)```", re.IGNORECASE | re.DOTALL)


def _text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _brief_path(challenge: Challenge) -> Path:
    return paths.loop_audit_dir() / challenge.loop_dir / "research-brief.md"


def brief_meta(challenge: Challenge) -> dict[str, Any]:
    path = _brief_path(challenge)
    text = path.read_text(errors="replace") if path.exists() else ""
    sql_blocks = [block.strip() for block in SQL_BLOCK_RE.findall(text)]
    status = (STATUS_RE.search(text).group(1).strip() if STATUS_RE.search(text) else challenge.status_default)
    presentation = (
        PRESENTATION_RE.search(text).group(1).strip()
        if PRESENTATION_RE.search(text)
        else challenge.ai_native_pattern
    )
    return {
        "exists": path.exists(),
        "path": str(path.relative_to(paths.root())) if path.exists() else None,
        "public_path": f"/briefs/{challenge.id:02d}-{challenge.slug}.md",
        "sha256": _text_sha(text) if text else None,
        "words": len(re.findall(r"\S+", text)),
        "complete_marker": text.startswith("<status>COMPLETE</status>"),
        "current_executable_status": status,
        "presentation_sentence": presentation,
        "sql_blocks": [
            {"index": idx + 1, "sql_hash": sql_hash(sql), "preview": sql[:600]}
            for idx, sql in enumerate(sql_blocks)
        ],
        "sql_block_count": len(sql_blocks),
    }


def all_findings() -> list[dict[str, Any]]:
    data = read_json(paths.findings_dir() / "verified.json", {})
    findings = data.get("findings")
    if isinstance(findings, list):
        return findings
    out: list[dict[str, Any]] = []
    for path in sorted(paths.findings_dir().glob("*.json")):
        if path.name in {"correlated.json", "verified.json", "neotoma-payload.json", "execution-proof.json"}:
            continue
        item = read_json(path, {})
        out.extend(item.get("findings", []))
    return out


def finding_summary(finding: dict[str, Any]) -> dict[str, Any]:
    evidence = (finding.get("evidence") or [{}])[0]
    sql = evidence.get("sql") or ""
    return {
        "finding_id": finding.get("finding_id"),
        "challenge": finding.get("challenge"),
        "entity": finding.get("entity"),
        "entity_type": finding.get("entity_type"),
        "claim": finding.get("claim"),
        "story_type": finding.get("story_type"),
        "lens": finding.get("lens"),
        "severity": finding.get("severity"),
        "confidence": finding.get("confidence"),
        "status": finding.get("status"),
        "support_status": finding.get("support_status"),
        "verification": {
            "replayed": finding.get("verification", {}).get("replayed"),
            "checked_at": finding.get("verification", {}).get("checked_at"),
        },
        "evidence": {
            "table": evidence.get("table"),
            "summary": evidence.get("summary"),
            "metrics": evidence.get("metrics", {}),
            "sql_hash": sql_hash(sql) if sql else None,
        },
    }


def findings_by_challenge() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in all_findings():
        grouped[str(finding.get("challenge"))].append(finding)
    for rows in grouped.values():
        rows.sort(
            key=lambda item: (
                {"high": 3, "medium": 2, "low": 1}.get(str(item.get("severity")), 0),
                float(item.get("confidence") or 0),
            ),
            reverse=True,
        )
    return grouped


def execution_map() -> dict[int, dict[str, Any]]:
    data = read_json(paths.findings_dir() / "execution-proof.json", {})
    out = {}
    for proof in data.get("proofs", []):
        out[int(proof["challenge_id"])] = proof
    return out


def challenge_container(challenge: Challenge) -> dict[str, Any]:
    meta = brief_meta(challenge)
    proofs = execution_map()
    proof = proofs.get(challenge.id)
    grouped = findings_by_challenge()
    matching: list[dict[str, Any]] = []
    for finding_challenge in challenge.finding_challenges:
        matching.extend(grouped.get(finding_challenge, []))
    matching = matching[:8]
    summarized_findings = [finding_summary(finding) for finding in matching]
    proof_tables = (proof or {}).get("tables_joined", {})
    tables = proof_tables.get("tables") or list(challenge.direct_tables)
    proof_level = (proof or {}).get("proof_level") or "schema-safe"
    execution_status = (proof or {}).get("status") or "not_executed"
    missing = list((proof or {}).get("missing", []))
    roadblocks = list(dict.fromkeys(list(challenge.roadblocks) + missing))
    hero = summarized_findings[0] if summarized_findings else None
    if not hero and proof and proof.get("result", {}).get("rows"):
        hero = {
            "finding_id": f"execution-proof:{challenge.id:02d}",
            "challenge": challenge.slug,
            "entity": proof["result"]["rows"][0].get("canonical_name")
            or proof["result"]["rows"][0].get("legal_name")
            or proof["result"]["rows"][0].get("ministry")
            or proof["result"]["rows"][0].get("owner_org_title")
            or "cohort",
            "claim": review_lead_claim(challenge, proof),
            "story_type": "operating_insight",
            "lens": "execution_proof",
            "severity": "medium",
            "evidence": {
                "table": ", ".join(tables),
                "summary": "Direct Postgres probe executed and stored as execution proof.",
                "metrics": proof["result"]["rows"][0],
                "sql_hash": proof["result"].get("sql_hash"),
            },
        }
    return {
        "challenge_id": challenge.id,
        "slug": challenge.slug,
        "route": f"/challenges/{challenge.id:02d}-{challenge.slug}.html",
        "name": challenge.name,
        "challenge_statement": challenge.challenge_statement,
        "artifact_type": challenge.artifact_type,
        "status": meta["current_executable_status"],
        "proof_level": proof_level,
        "execution_status": execution_status,
        "ai_native_pattern": challenge.ai_native_pattern,
        "presentation_sentence": meta["presentation_sentence"],
        "tables_joined": {"count": len(tables), "tables": tables},
        "roadblocks": roadblocks,
        "hero_finding": hero,
        "findings": summarized_findings,
        "execution_proof": {
            "available": bool(proof),
            "probe": (proof or {}).get("probe"),
            "result_preview": (proof or {}).get("result", {}).get("rows", [])[:5],
            "sql_hash": (proof or {}).get("result", {}).get("sql_hash"),
            "elapsed_ms": (proof or {}).get("result", {}).get("elapsed_ms"),
            "ok": (proof or {}).get("result", {}).get("ok"),
            "error": (proof or {}).get("result", {}).get("error"),
        },
        "brief": meta,
        "decision_prompt": decision_prompt(challenge, execution_status),
        "claim_safety": claim_safety(challenge),
    }


def review_lead_claim(challenge: Challenge, proof: dict[str, Any]) -> str:
    count = proof.get("result", {}).get("rows_returned", 0)
    if challenge.status_default == "NEEDS_EXTERNAL_DATA":
        return (
            f"The source-data query returned {count} records, but this check needs an outside source "
            "before any review lead can be promoted."
        )
    if challenge.status_default == "RUNNABLE_WITH_EXTRA_MATERIALIZATION":
        return (
            f"The source-data query returned {count} records for review. A prepared dataset or follow-up "
            "source is still needed before escalation."
        )
    return f"The source-data query returned {count} records for review."


def decision_prompt(challenge: Challenge, execution_status: str) -> str:
    if "external_needed" in execution_status or challenge.status_default == "NEEDS_EXTERNAL_DATA":
        return "Do we authorize the external evidence fetch needed to turn this into a review lead?"
    if "roadblocks" in execution_status or challenge.status_default == "RUNNABLE_WITH_EXTRA_MATERIALIZATION":
        return "Is this worth one more materialization pass before presentation or review?"
    return "Should this be promoted, held for review, or rejected?"


def claim_safety(challenge: Challenge) -> str:
    if challenge.id == 1:
        return "Say stale filing or stopped filing. Do not say dissolved, bankrupt, or disappeared without registry evidence."
    if challenge.id == 6:
        return "Say name-overlap lead. Do not say control or conflict without identity validation."
    if challenge.id == 10:
        return "Say internal data-quality signal unless external regulator, court, sanctions, or media evidence is attached."
    return "Use review lead language unless the execution proof and countercheck support a stronger claim."


def build_challenges() -> dict[str, Any]:
    cards = [challenge_container(challenge) for challenge in CHALLENGES]
    statuses = Counter(card["status"] for card in cards)
    proof_levels = Counter(card["proof_level"] for card in cards)
    return {
        "generated_at": now_iso(),
        "count": len(cards),
        "status_counts": dict(statuses),
        "proof_level_counts": dict(proof_levels),
        "cards": cards,
    }


def build_audit_summary() -> dict[str, Any]:
    cards = [brief_meta(challenge) for challenge in CHALLENGES]
    audit_path = paths.web_dir() / "agency-loop-audit.html"
    return {
        "generated_at": now_iso(),
        "source": str(audit_path.relative_to(paths.root())) if audit_path.exists() else None,
        "source_sha256": _text_sha(audit_path.read_text(errors="replace")) if audit_path.exists() else None,
        "note": "Lexical/schema audit. Execution proof is tracked separately.",
        "known_bad_references": 0,
        "suspect_schema_references": 0,
        "placeholder_signals": 0,
        "cards": cards,
    }
