from __future__ import annotations

from typing import Any

from . import paths
from .jsonio import read_json
from .util import first_match


def registry() -> list[dict[str, Any]]:
    data = read_json(paths.root() / "config" / "skills.json", {"skills": []})
    return data.get("skills", [])


def table_columns(profile: dict[str, Any]) -> list[str]:
    return [col["name"] for col in profile.get("columns", [])]


def match_required_fields(skill: dict[str, Any], profile: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    cols = table_columns(profile)
    field_map: dict[str, str] = {}
    missing: list[str] = []
    for req in skill.get("requires", []):
        semantic = req["semantic"]
        match = first_match(cols, req.get("aliases", []))
        if match:
            field_map[semantic] = match
        else:
            missing.append(semantic)
    for opt in skill.get("optional", []):
        semantic = opt["semantic"]
        match = first_match(cols, opt.get("aliases", []))
        if match:
            field_map[semantic] = match
    return field_map, missing


def evaluate_skill(skill: dict[str, Any], profiles: list[dict[str, Any]]) -> dict[str, Any]:
    supported_tables: list[dict[str, Any]] = []
    missing_by_table: dict[str, list[str]] = {}

    for profile in profiles:
        field_map, missing = match_required_fields(skill, profile)
        if not missing:
            supported_tables.append(
                {
                    "table": profile["table"],
                    "row_count": profile.get("row_count"),
                    "field_map": field_map,
                }
            )
        else:
            missing_by_table[profile["table"]] = missing

    all_required = [req["semantic"] for req in skill.get("requires", [])]
    found_semantics = sorted({semantic for table in supported_tables for semantic in table["field_map"]})
    missing_semantics = [semantic for semantic in all_required if semantic not in found_semantics]
    return {
        "skill": skill["name"],
        "status": skill.get("status", "unknown"),
        "command": skill.get("command"),
        "supported": len(supported_tables) > 0,
        "supported_tables": supported_tables,
        "missing_semantics": missing_semantics,
        "missing_by_table": missing_by_table,
    }


def applicability_matrix(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [evaluate_skill(skill, profiles) for skill in registry()]
