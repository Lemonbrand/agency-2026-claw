from __future__ import annotations

import json
from typing import Any

from . import brain, ledger, paths
from .jsonio import read_json, write_json
from .util import now_iso


STORY_TYPES = {"risk", "opportunity", "capacity", "policy_gap", "success", "operating_insight"}


def _evidence(finding: dict[str, Any]) -> dict[str, Any]:
    return (finding.get("evidence") or [{}])[0]


def _metric(finding: dict[str, Any], key: str, default: Any = None) -> Any:
    metrics = _evidence(finding).get("metrics") or {}
    return metrics.get(key, default)


def _packet_for_vendor_concentration(finding: dict[str, Any]) -> dict[str, Any]:
    share = float(_metric(finding, "share", 0) or 0)
    group = _metric(finding, "group_key", "this category")
    row_count = int(_metric(finding, "row_count", 0) or 0)
    vendor = finding.get("entity", "the top vendor")
    framework_caveat = row_count >= 50
    lens = "centrality" if framework_caveat else "concentration"
    return {
        "story_type": "operating_insight" if framework_caveat else "risk",
        "lens": lens,
        "what_happened": f"{vendor} holds {share:.1%} of spend in {group}.",
        "why_it_matters": (
            "Concentrated spend can mean weak competition, threshold avoidance, or a deliberate "
            "framework contract. The story turns on which one is true."
        ),
        "who_is_affected": "The procuring department, competing vendors, and any program relying on this category.",
        "evidence_summary": _evidence(finding).get("summary", ""),
        "what_could_disprove": (
            "If this category is too narrow to support a claim, or this is a national framework "
            "contract designed for a single delivery partner, the lens flips from concentration to centrality."
        ),
        "what_to_check_next": "Pull procurement method, RFP history, framework status, and bidder count for this category.",
        "decision_enabled": "Decide whether the procurement design is deliberate or has drifted into incumbency.",
    }


def _packet_for_amendment_creep(finding: dict[str, Any]) -> dict[str, Any]:
    multiple = float(_metric(finding, "multiple", 1) or 1)
    contract_ref = _metric(finding, "contract_ref", "this contract")
    return {
        "story_type": "risk",
        "lens": "post_award_growth",
        "what_happened": f"Contract {contract_ref} grew {multiple:.1f}x its original awarded value through amendments.",
        "why_it_matters": (
            "Large post-award growth can indicate weak initial scoping, scope drift, or competitive "
            "thresholds being avoided through amendments rather than recompete."
        ),
        "who_is_affected": "The procuring department and the vendors who lost the original bid at a smaller value.",
        "evidence_summary": _evidence(finding).get("summary", ""),
        "what_could_disprove": (
            "If the original value was a placeholder, or amendments fund distinct phases authorized "
            "under the original procurement, the lens shifts to scope evolution rather than creep."
        ),
        "what_to_check_next": "Pull amendment approvals, scope-change rationale, and the original procurement method.",
        "decision_enabled": "Decide whether to recompete or to document a scope-evolution justification.",
    }


def _packet_for_related_parties(finding: dict[str, Any]) -> dict[str, Any]:
    org_count = int(_metric(finding, "org_count", 2) or 2)
    person = finding.get("entity", "this name")
    orgs = _metric(finding, "orgs", "")
    return {
        "story_type": "operating_insight",
        "lens": "name_overlap_review",
        "what_happened": f"The name '{person}' appears across {org_count} organizations in the loaded data.",
        "why_it_matters": (
            "Name overlap is a review lead, not a finding. It can reveal genuine governance ties or "
            "a same-name coincidence. Either way it tells a system whether identifier discipline is in place."
        ),
        "who_is_affected": "Anyone relying on conflict-of-interest disclosures or beneficial-ownership registers tied to this dataset.",
        "evidence_summary": (
            f"Name match across multiple organizations: {orgs}." if orgs else "Name match across multiple organizations."
        ),
        "what_could_disprove": "Any unique identifier (person ID, DOB, declared affiliation) showing these are different people.",
        "what_to_check_next": "Validate identity using person identifiers or external registries before treating this as a governance signal.",
        "decision_enabled": "Decide whether to add identifier discipline to procurement and grant intake.",
    }


def _generic_packet(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "story_type": finding.get("story_type", "risk"),
        "lens": finding.get("lens", "unclassified"),
        "what_happened": finding.get("claim", ""),
        "why_it_matters": "Reviewer language has not been generated for this challenge yet.",
        "who_is_affected": "Unknown without further analysis.",
        "evidence_summary": _evidence(finding).get("summary", ""),
        "what_could_disprove": "Run a disconfirming check or compare against peer findings.",
        "what_to_check_next": "Open the evidence trail and replay the SQL.",
        "decision_enabled": "Pending review.",
    }


PACKET_BUILDERS = {
    "vendor_concentration": _packet_for_vendor_concentration,
    "amendment_creep": _packet_for_amendment_creep,
    "related_parties": _packet_for_related_parties,
}


def heuristic_story_packet(finding: dict[str, Any]) -> dict[str, Any]:
    builder = PACKET_BUILDERS.get(finding.get("challenge"), _generic_packet)
    packet = builder(finding)
    packet["finding_id"] = finding.get("finding_id")
    packet["entity"] = finding.get("entity")
    packet["support_status"] = finding.get("support_status")
    return packet


def heuristic_review() -> dict[str, Any]:
    findings = read_json(paths.findings_dir() / "verified.json", {"findings": []}).get("findings", [])
    stories = [heuristic_story_packet(finding) for finding in findings]

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
                    "severity": "low",
                    "finding_id": finding.get("finding_id"),
                    "critique": "Related-party signal is name-based. Present as identity validation, not a governance finding.",
                }
            )

    return {
        "generated_at": now_iso(),
        "reviewer": "heuristic",
        "approved_for_demo": True,
        "stories": stories,
        "issues": issues,
        "recommended_language": (
            "Use review lead, validate, and needs human review. Do not say fraud or wrongdoing. "
            "Frame each story as either a risk worth checking, an opportunity worth exploring, or "
            "an operating insight that informs a decision."
        ),
    }


def _review_payload() -> dict[str, Any]:
    plan = read_json(paths.state_dir() / "investigation-plan.json", {})
    checks = read_json(paths.findings_dir() / "disconfirming-checks.json", {})
    verified = read_json(paths.findings_dir() / "verified.json", {})

    findings_summary = []
    for finding in verified.get("findings", [])[:25]:
        findings_summary.append(
            {
                "finding_id": finding.get("finding_id"),
                "challenge": finding.get("challenge"),
                "entity": finding.get("entity"),
                "claim": finding.get("claim"),
                "severity": finding.get("severity"),
                "support_status": finding.get("support_status"),
                "story_type": finding.get("story_type"),
                "lens": finding.get("lens"),
                "metrics": (finding.get("evidence") or [{}])[0].get("metrics", {}),
            }
        )

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
        "findings": findings_summary,
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
You are the story-shaping brain for LemonClaw, a public-interest accountability story engine.

Return JSON only. No markdown, no prose outside the JSON.

You will receive an investigation plan, the verified findings, and the disconfirming-check results.

For each finding, write a seven-field story packet. Classify story_type as one of:
- risk
- opportunity
- capacity
- policy_gap
- success
- operating_insight

Then assign a short lens label (e.g. concentration, post_award_growth, name_overlap_review,
underserved_region, consistent_delivery, scale_up_potential, thin_delivery_capacity,
commitment_vs_allocation, centrality).

Override the detector's default story_type when the metrics warrant it. For example, vendor
concentration with high row_count may be a centrality / operating_insight story rather than a risk.

Be honest when the finding is weak. Honor disconfirming-check status. Use "review lead",
"validate", "needs human review". Never say fraud, illegal, or wrongdoing.

Output shape:
{{
  "generated_at": "",
  "reviewer": "claude",
  "approved_for_demo": true,
  "stories": [
    {{
      "finding_id": "...",
      "entity": "...",
      "story_type": "risk|opportunity|capacity|policy_gap|success|operating_insight",
      "lens": "short snake_case label",
      "what_happened": "one sentence in plain English",
      "why_it_matters": "one or two sentences",
      "who_is_affected": "one sentence naming the affected actors",
      "evidence_summary": "one sentence summarizing the metric trail",
      "what_could_disprove": "one sentence on what would weaken this story",
      "what_to_check_next": "one concrete next step a human can take",
      "decision_enabled": "one sentence on the decision this story unlocks"
    }}
  ],
  "issues": [
    {{ "severity": "low|medium|high", "finding_id": "... or null", "critique": "..." }}
  ],
  "recommended_language": "..."
}}

Payload:
{json.dumps(payload, indent=2)}
"""
    review = brain.claude_json(prompt, timeout_s=120)
    review["generated_at"] = review.get("generated_at") or now_iso()
    review["reviewer"] = "claude"
    if "stories" not in review:
        review["stories"] = []
    for story in review["stories"]:
        if story.get("story_type") not in STORY_TYPES:
            story["story_type"] = "risk"
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
    ledger.event(
        "review_completed",
        {
            "reviewer": out.get("reviewer"),
            "stories": len(out.get("stories", [])),
            "issues": len(out.get("issues", [])),
        },
    )
    return out
