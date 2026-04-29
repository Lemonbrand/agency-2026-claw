from __future__ import annotations

from typing import Any

from . import dataset, ledger, paths
from .jsonio import write_json
from .util import now_iso


def verify_findings() -> list[dict[str, Any]]:
    con = dataset.connect()
    findings = ledger.load_all_findings()
    verified: list[dict[str, Any]] = []

    for finding in findings:
        checks: list[dict[str, Any]] = []
        ok = True
        for evidence in finding.get("evidence", []):
            sql = evidence.get("sql")
            if not sql:
                ok = False
                checks.append({"ok": False, "reason": "missing_sql"})
                continue
            try:
                count = len(con.execute(sql).fetchall())
                checks.append({"ok": count > 0, "row_count": count})
                ok = ok and count > 0
            except Exception as exc:
                ok = False
                checks.append({"ok": False, "reason": str(exc)})

        finding = dict(finding)
        finding["verification"] = {
            **finding.get("verification", {}),
            "replayed": ok,
            "checked_at": now_iso(),
            "checks": checks,
        }
        verified.append(finding)

    write_json(
        paths.findings_dir() / "verified.json",
        {"generated_at": now_iso(), "count": len(verified), "findings": verified},
    )
    ledger.event("verified", {"count": len(verified)})
    return verified
