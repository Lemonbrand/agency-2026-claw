from __future__ import annotations

from collections import defaultdict
from typing import Any

from . import ledger, paths
from .jsonio import read_json, write_json
from .resolution import entity_to_cluster
from .util import now_iso


def correlate() -> dict[str, Any]:
    verified = read_json(paths.findings_dir() / "verified.json", None)
    findings = verified.get("findings", []) if verified else ledger.load_all_findings()
    by_entity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    clusters = entity_to_cluster()

    for finding in findings:
        entity = str(finding.get("entity", "unknown"))
        by_entity[clusters.get(entity, entity)].append(finding)

    ranked = []
    for entity, rows in by_entity.items():
        challenges = sorted({row.get("challenge") for row in rows})
        severity_weight = sum({"low": 1, "medium": 2, "high": 3}.get(row.get("severity"), 1) for row in rows)
        replayed = sum(1 for row in rows if row.get("verification", {}).get("replayed"))
        contested = sum(1 for row in rows if row.get("support_status") == "contested")
        supported = sum(1 for row in rows if row.get("support_status") == "supported")
        ranked.append(
            {
                "entity": entity,
                "score": len(challenges) * 10 + severity_weight + replayed + supported - contested,
                "challenge_count": len(challenges),
                "challenges": challenges,
                "finding_ids": [row.get("finding_id") for row in rows],
                "claims": [row.get("claim") for row in rows],
                "support": {
                    "supported": supported,
                    "contested": contested,
                    "not_checked": sum(1 for row in rows if row.get("support_status") in {None, "not_checked"}),
                },
                "members": sorted({str(row.get("entity", "unknown")) for row in rows}),
            }
        )

    ranked.sort(key=lambda row: row["score"], reverse=True)
    out = {"generated_at": now_iso(), "entities": ranked}
    write_json(paths.findings_dir() / "correlated.json", out)
    ledger.event("correlated", {"entity_count": len(ranked)})
    return out
