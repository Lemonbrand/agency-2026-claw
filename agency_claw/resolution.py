from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from . import brain, ledger, paths
from .jsonio import read_json, write_json
from .util import now_iso


SUFFIX_RE = re.compile(r"\b(inc|incorporated|ltd|limited|corp|corporation|co|company|llc|lp)\b\.?", re.I)


def normalize_name(name: str) -> str:
    value = SUFFIX_RE.sub("", name)
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", value)


def surfaced_entities() -> list[str]:
    findings = read_json(paths.findings_dir() / "verified.json", {"findings": []}).get("findings", [])
    return sorted({str(row.get("entity")) for row in findings if row.get("entity")})


def heuristic_clusters() -> dict[str, Any]:
    groups: dict[str, list[str]] = defaultdict(list)
    for name in surfaced_entities():
        groups[normalize_name(name)].append(name)

    clusters = []
    for key, members in groups.items():
        canonical = sorted(members, key=lambda x: (len(x), x))[0]
        clusters.append(
            {
                "canonical": canonical,
                "members": sorted(members),
                "confidence": 0.95 if len(members) == 1 else 0.78,
                "status": "exact_or_normalized_match" if len(members) > 1 else "single_name",
                "reason": "Normalized legal suffix and punctuation only.",
            }
        )
    return {"generated_at": now_iso(), "brain": "heuristic", "clusters": clusters}


def codex_clusters() -> dict[str, Any]:
    names = surfaced_entities()
    prompt = f"""
You are doing cautious entity resolution for an audit workbench.

Return JSON only. Do not use markdown.

Cluster likely-same entity names from this small surfaced list. Do not over-merge. If unsure, keep separate. Every cluster needs a status: single_name, possible_same_entity, or likely_same_entity.

Output shape:
{{"generated_at":"","brain":"codex","clusters":[{{"canonical":"...","members":["..."],"confidence":0.0,"status":"...","reason":"..."}}]}}

Names:
{json.dumps(names, indent=2)}
"""
    data = brain.codex_json(prompt)
    data["generated_at"] = data.get("generated_at") or now_iso()
    data["brain"] = "codex"
    return data


def resolve_entities(brain_name: str = "heuristic") -> dict[str, Any]:
    if brain_name == "codex":
        out = codex_clusters()
    elif brain_name == "heuristic":
        out = heuristic_clusters()
    else:
        raise ValueError(f"unsupported resolver brain: {brain_name}")

    write_json(paths.state_dir() / "entity-clusters.json", out)
    ledger.event("entity_resolution_completed", {"brain": out.get("brain"), "clusters": len(out.get("clusters", []))})
    return out


def entity_to_cluster() -> dict[str, str]:
    clusters = read_json(paths.state_dir() / "entity-clusters.json", {"clusters": []}).get("clusters", [])
    out = {}
    for cluster in clusters:
        canonical = cluster.get("canonical")
        for member in cluster.get("members", []):
            out[str(member)] = str(canonical)
    return out
