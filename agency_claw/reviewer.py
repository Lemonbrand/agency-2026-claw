from __future__ import annotations

import json
from typing import Any

from . import brain, ledger, paths
from .jsonio import read_json, write_json
from .util import now_iso


def heuristic_review() -> dict[str, Any]:
    findings = read_json(paths.findings_dir() / "verified.json", {"findings": []}).get("findings", [])
    issues = []
    for finding in findings:
        if finding.get("support_status") == "contested":
            issues.append(
                {
                    "severity": "medium",
                    "finding_id": finding.get("finding_id"),
                    "critique": "Disconfirming check contested or contextualized this lead. Keep it in validate status.",
                }
            )
        if finding.get("challenge") == "related_parties":
            issues.append(
                {
                    "severity": "medium",
                    "finding_id": finding.get("finding_id"),
                    "critique": "Related-party signal is name-based. Present as identity validation, not a governance finding.",
                }
            )
    return {
        "generated_at": now_iso(),
        "reviewer": "heuristic",
        "approved_for_demo": True,
        "issues": issues,
        "recommended_language": "Use review lead, validate, and needs human review. Do not say fraud or wrongdoing.",
    }


def _review_payload() -> dict[str, Any]:
    plan = read_json(paths.state_dir() / "investigation-plan.json", {})
    checks = read_json(paths.findings_dir() / "disconfirming-checks.json", {})
    correlated = read_json(paths.findings_dir() / "correlated.json", {})
    verified = read_json(paths.findings_dir() / "verified.json", {})

    return {
        "plan": {
            "brain": plan.get("brain"),
            "selected": [
                {"skill": item.get("skill"), "reason": item.get("reason")}
                for item in plan.get("selected", [])
            ],
            "rejected": [
                {"skill": item.get("skill"), "reason": item.get("reason")}
                for item in plan.get("rejected", [])
            ],
        },
        "correlated": {
            "entities": [
                {
                    "entity": item.get("entity"),
                    "score": item.get("score"),
                    "challenges": item.get("challenges"),
                    "support": item.get("support"),
                    "claims": item.get("claims", [])[:3],
                }
                for item in correlated.get("entities", [])[:10]
            ]
        },
        "findings": [
            {
                "finding_id": item.get("finding_id"),
                "challenge": item.get("challenge"),
                "entity": item.get("entity"),
                "claim": item.get("claim"),
                "severity": item.get("severity"),
                "support_status": item.get("support_status"),
                "replayed": bool(item.get("verification", {}).get("replayed")),
            }
            for item in verified.get("findings", [])[:25]
        ],
        "disconfirming_checks": {
            "summary": checks.get("summary"),
            "checks": [
                {
                    "finding_id": item.get("finding_id"),
                    "question": item.get("question"),
                    "status": item.get("status"),
                    "interpretation": item.get("interpretation"),
                }
                for item in checks.get("checks", [])[:25]
            ],
        },
    }


def claude_review() -> dict[str, Any]:
    payload = _review_payload()
    prompt = f"""
You are the skeptical second-pass reviewer for a government accountability demo.

Return JSON only. Do not use markdown.

Review the selected skills, rejected skills, findings, disconfirming checks, and ranked queue. Flag claims that are too strong, weakly supported, or missing caveats. Keep it short.

Output shape:
{{"generated_at":"","reviewer":"claude","approved_for_demo":true,"issues":[{{"severity":"low|medium|high","finding_id":"... or null","critique":"..."}}],"recommended_language":"..."}}

Payload:
{json.dumps(payload, indent=2)}
"""
    review = brain.claude_json(prompt, timeout_s=90)
    review["generated_at"] = review.get("generated_at") or now_iso()
    review["reviewer"] = "claude"
    return review


def review(reviewer_name: str = "heuristic") -> dict[str, Any]:
    if reviewer_name == "claude":
        try:
            out = claude_review()
        except brain.BrainError as exc:
            out = heuristic_review()
            out["reviewer"] = "heuristic_fallback"
            out["claude_error"] = str(exc)
    elif reviewer_name == "heuristic":
        out = heuristic_review()
    else:
        raise ValueError(f"unsupported reviewer: {reviewer_name}")

    write_json(paths.state_dir() / "review.json", out)
    ledger.event("review_completed", {"reviewer": out.get("reviewer"), "issues": len(out.get("issues", []))})
    return out
