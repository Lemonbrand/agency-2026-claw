from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from . import paths
from .jsonio import read_json, write_json
from .util import now_iso


def tenant_id() -> str:
    return os.environ.get("AGENCY_TENANT_ID", "agency-2026-local")


def neotoma_script() -> Path:
    return paths.root() / "scripts" / "neotoma.sh"


def build_payload() -> list[dict[str, Any]]:
    findings_doc = read_json(paths.findings_dir() / "verified.json", None)
    findings = findings_doc.get("findings", []) if findings_doc else []
    if not findings:
        findings = read_json(paths.findings_dir() / "correlated.json", {}).get("findings", [])

    manifest = read_json(paths.state_dir() / "dataset-manifest.json", [])
    profiles = read_json(paths.state_dir() / "discovered.schema.json", [])
    plan = read_json(paths.state_dir() / "investigation-plan.json", {})
    clusters = read_json(paths.state_dir() / "entity-clusters.json", {})
    review = read_json(paths.state_dir() / "review.json", {})
    disconfirming = read_json(paths.findings_dir() / "disconfirming-checks.json", {})
    correlated = read_json(paths.findings_dir() / "correlated.json", {})

    entities: list[dict[str, Any]] = [
        {
            "entity_type": "investigation",
            "name": "Agency 2026 Local Investigation",
            "status": "active",
            "occurred_at": now_iso(),
            "dataset_count": len(manifest),
            "profile_count": len(profiles),
            "plan": plan,
            "entity_clusters": clusters,
            "review": review,
            "disconfirming_checks": disconfirming,
            "correlated_queue": correlated,
        }
    ]

    for source in manifest:
        entities.append(
            {
                "entity_type": "dataset_source",
                "name": source.get("source_name") or source.get("table") or "unknown",
                "table": source.get("table"),
                "sha256": source.get("source_sha256"),
                "bytes": source.get("source_bytes"),
                "parquet_path": source.get("parquet_path"),
                "source_schema": source.get("source_schema"),
                "row_count": source.get("row_count"),
                "elapsed_s": source.get("elapsed_s"),
            }
        )

    for finding in findings:
        entities.append(
            {
                "entity_type": "finding",
                "name": finding.get("finding_id"),
                "challenge": finding.get("challenge"),
                "subject": finding.get("entity"),
                "subject_type": finding.get("entity_type"),
                "claim": finding.get("claim"),
                "severity": finding.get("severity"),
                "confidence": finding.get("confidence"),
                "status": finding.get("status"),
                "support_status": finding.get("support_status"),
                "evidence": finding.get("evidence", []),
                "verification": finding.get("verification", {}),
                "disconfirming_checks": finding.get("disconfirming_checks", []),
            }
        )

    return entities


def promote() -> subprocess.CompletedProcess[str]:
    payload = build_payload()
    payload_path = paths.findings_dir() / "neotoma-payload.json"
    write_json(payload_path, payload)
    return subprocess.run(
        [
            str(neotoma_script()),
            "--offline",
            "store",
            "--user-id",
            tenant_id(),
            "--file",
            str(payload_path),
            "--idempotency-key",
            f"agency-2026-promote-{len(payload)}",
        ],
        cwd=str(paths.root()),
        text=True,
        capture_output=True,
        check=False,
    )
