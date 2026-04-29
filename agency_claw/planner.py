from __future__ import annotations

import json
from typing import Any

from . import brain, ledger, paths
from .jsonio import read_json, write_json
from .skills import applicability_matrix, registry
from .util import now_iso


def plan_path() -> Any:
    return paths.state_dir() / "investigation-plan.json"


def heuristic_plan() -> dict[str, Any]:
    profiles = read_json(paths.state_dir() / "discovered.schema.json", [])
    matrix = applicability_matrix(profiles)
    by_name = {skill["name"]: skill for skill in registry()}
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for item in matrix:
        skill = by_name[item["skill"]]
        if item["supported"] and skill.get("status") == "implemented" and skill.get("command"):
            selected.append(
                {
                    "skill": skill["name"],
                    "command": skill["command"],
                    "priority": skill.get("priority", 999),
                    "reason": f"Required fields found in {len(item['supported_tables'])} table(s).",
                    "supported_tables": item["supported_tables"],
                }
            )
        else:
            if not item["supported"]:
                missing = ", ".join(item["missing_semantics"]) or "required fields"
                reason = f"Required fields not found: {missing}."
                if skill.get("status") != "implemented":
                    reason = f"Detector is not implemented and required fields are missing: {missing}."
            elif skill.get("status") != "implemented":
                reason = "Required fields appear present, but detector is not implemented for the local demo path."
            else:
                reason = "No runnable command declared."
            rejected.append(
                {
                    "skill": skill["name"],
                    "status": skill.get("status"),
                    "reason": reason,
                    "missing_semantics": item["missing_semantics"],
                    "supported_tables": item["supported_tables"],
                }
            )

    selected.sort(key=lambda row: row["priority"])
    return {
        "generated_at": now_iso(),
        "brain": "heuristic",
        "selected": selected,
        "rejected": rejected,
        "notes": [
            "Heuristic planner used. Use --brain codex for model-driven selection and ordering.",
            "Rejected skills are recorded as evidence of restraint, not failure.",
        ],
    }


def codex_plan() -> dict[str, Any]:
    profiles = read_json(paths.state_dir() / "discovered.schema.json", [])
    skills = registry()
    matrix = applicability_matrix(profiles)
    prompt = f"""
You are the planning brain for LemonClaw, a public-interest accountability story engine.

Return JSON only. Do not wrap it in markdown.

You will receive:
- schema profiles for loaded datasets
- a skill registry
- a deterministic applicability matrix

Your task:
1. Select only skills that can run from the available data.
2. Reject unsupported skills with concrete reasons.
3. Order selected skills for a one-day presentation build.
4. Do not pretend a missing column exists.
5. Prefer implemented skills. Stub skills can only be rejected or listed as future_work.

Output shape:
{{
  "generated_at": "use current timestamp if known, otherwise leave blank",
  "brain": "codex",
  "selected": [
    {{
      "skill": "skill-name",
      "command": "command-name",
      "priority": 10,
      "reason": "why the schema supports it",
      "supported_tables": []
    }}
  ],
  "rejected": [
    {{
      "skill": "skill-name",
      "status": "implemented|stub",
      "reason": "why it cannot or should not run",
      "missing_semantics": [],
      "supported_tables": []
    }}
  ],
  "notes": []
}}

Schema profiles:
{json.dumps(profiles, indent=2)}

Skill registry:
{json.dumps(skills, indent=2)}

Applicability matrix:
{json.dumps(matrix, indent=2)}
"""
    plan = brain.codex_json(prompt)
    plan["generated_at"] = plan.get("generated_at") or now_iso()
    plan["brain"] = "codex"
    return hydrate_plan(plan, matrix)


def hydrate_plan(plan: dict[str, Any], matrix: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    profiles = read_json(paths.state_dir() / "discovered.schema.json", [])
    matrix = matrix or applicability_matrix(profiles)
    matrix_by_skill = {row["skill"]: row for row in matrix}
    registry_by_skill = {row["name"]: row for row in registry()}

    for item in plan.get("selected", []):
        skill_name = item.get("skill")
        reg = registry_by_skill.get(skill_name, {})
        app = matrix_by_skill.get(skill_name, {})
        item["command"] = item.get("command") or reg.get("command")
        item["priority"] = item.get("priority") or reg.get("priority", 999)
        if not item.get("supported_tables"):
            item["supported_tables"] = app.get("supported_tables", [])

    for item in plan.get("rejected", []):
        skill_name = item.get("skill")
        reg = registry_by_skill.get(skill_name, {})
        app = matrix_by_skill.get(skill_name, {})
        item["status"] = item.get("status") or reg.get("status")
        if "missing_semantics" not in item:
            item["missing_semantics"] = app.get("missing_semantics", [])
        if "supported_tables" not in item:
            item["supported_tables"] = app.get("supported_tables", [])

    return plan


def create_plan(brain_name: str = "heuristic") -> dict[str, Any]:
    paths.ensure_dirs()
    if brain_name == "codex":
        plan = codex_plan()
    elif brain_name == "heuristic":
        plan = hydrate_plan(heuristic_plan())
    else:
        raise ValueError(f"unsupported planner brain: {brain_name}")

    write_json(plan_path(), plan)
    ledger.event(
        "plan_created",
        {
            "brain": plan.get("brain"),
            "selected": [row.get("skill") for row in plan.get("selected", [])],
            "rejected": [row.get("skill") for row in plan.get("rejected", [])],
        },
    )
    return plan


def load_plan() -> dict[str, Any]:
    plan = read_json(plan_path(), None)
    if not plan:
        raise SystemExit("No investigation plan. Run ./bin/agency plan first.")
    return plan
