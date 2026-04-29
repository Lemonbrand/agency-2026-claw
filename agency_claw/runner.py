from __future__ import annotations

from typing import Any

from . import detectors, hackathon, ledger
from .planner import load_plan


DETECTORS = {
    "vendor-concentration": detectors.vendor_concentration,
    "amendment-creep": detectors.amendment_creep,
    "related-parties": detectors.related_parties,
    "tri-jurisdictional-funding": hackathon.detect_tri_jurisdictional,
    "cra-loop-risk": hackathon.detect_funding_loops,
    "ab-sole-source-concentration": hackathon.detect_sole_source_concentration,
    "fed-amendment-creep": hackathon.detect_amendment_creep_fed,
    "cra-shared-directors": hackathon.detect_shared_directors,
}


def run_skill(command: str, limit: int = 20) -> list[dict[str, Any]]:
    if command not in DETECTORS:
        raise SystemExit(f"No local detector registered for command: {command}")
    return DETECTORS[command](limit=limit)


def run_plan(limit: int = 20) -> dict[str, Any]:
    plan = load_plan()
    runs = []
    for item in plan.get("selected", []):
        command = item.get("command")
        skill = item.get("skill")
        if not command:
            runs.append({"skill": skill, "command": command, "status": "skipped", "reason": "no command"})
            continue
        findings = run_skill(command, limit=limit)
        runs.append(
            {
                "skill": skill,
                "command": command,
                "status": "completed",
                "finding_count": len(findings),
                "reason": item.get("reason"),
            }
        )
        ledger.event("skill_run", runs[-1])

    result = {
        "plan_brain": plan.get("brain"),
        "runs": runs,
        "selected_count": len(plan.get("selected", [])),
        "rejected_count": len(plan.get("rejected", [])),
    }
    ledger.event("plan_run_completed", result)
    return result
