from __future__ import annotations

import json
from typing import Any

from . import brain, dataset, ledger, paths
from .duck import records
from .jsonio import read_json, write_json
from .planner import load_plan
from .util import now_iso, quote_ident, sql_literal


def _find_field_map(plan: dict[str, Any], skill: str, table: str) -> dict[str, str]:
    for item in plan.get("selected", []):
        if item.get("skill") != skill:
            continue
        for supported in item.get("supported_tables", []):
            if supported.get("table") == table:
                return supported.get("field_map", {})
    return {}


def _safe_sql(sql: str) -> str:
    stripped = sql.strip().rstrip(";")
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise ValueError("disconfirming SQL must be SELECT or WITH")
    forbidden = [" insert ", " update ", " delete ", " drop ", " create ", " alter ", " copy "]
    padded = f" {lowered} "
    if any(word in padded for word in forbidden):
        raise ValueError("disconfirming SQL contains a forbidden statement")
    return stripped


def heuristic_checks_for_finding(finding: dict[str, Any], plan: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = (finding.get("evidence") or [{}])[0]
    table = evidence.get("table")
    challenge = finding.get("challenge")
    metrics = evidence.get("metrics") or {}
    checks: list[dict[str, Any]] = []

    if challenge == "amendment_creep" and table:
        field_map = _find_field_map(plan, "amendment-creep", table)
        original = field_map.get("original_value")
        current = field_map.get("current_value")
        finding_multiple = metrics.get("multiple")
        if original and current:
            sql = f"""
WITH multiples AS (
  SELECT try_cast({quote_ident(current)} AS DOUBLE) / nullif(try_cast({quote_ident(original)} AS DOUBLE), 0) AS multiple
  FROM {quote_ident(table)}
  WHERE try_cast({quote_ident(original)} AS DOUBLE) > 0
)
SELECT
  quantile_cont(multiple, 0.95) AS p95_multiple,
  max(multiple) AS max_multiple,
  count(*) AS peer_count
FROM multiples
WHERE multiple IS NOT NULL
""".strip()
            checks.append(
                {
                    "finding_id": finding["finding_id"],
                    "question": "Is this increase still unusual compared with peers in the same table?",
                    "sql": sql,
                    "contested_if": f"p95_multiple >= finding_multiple ({finding_multiple})",
                    "status": "pending",
                }
            )

    if challenge == "vendor_concentration" and table:
        field_map = _find_field_map(plan, "vendor-concentration", table)
        vendor = field_map.get("vendor")
        amount = field_map.get("amount")
        category = field_map.get("category")
        group = metrics.get("group_key")
        if vendor and amount and category and group is not None:
            sql = f"""
SELECT
  count(DISTINCT CAST({quote_ident(vendor)} AS VARCHAR)) AS vendor_count,
  sum(try_cast({quote_ident(amount)} AS DOUBLE)) AS group_spend,
  count(*) AS row_count
FROM {quote_ident(table)}
WHERE CAST({quote_ident(category)} AS VARCHAR) = {sql_literal(group)}
  AND try_cast({quote_ident(amount)} AS DOUBLE) IS NOT NULL
""".strip()
            checks.append(
                {
                    "finding_id": finding["finding_id"],
                    "question": "Is the concentrated category too narrow to support a strong review claim?",
                    "sql": sql,
                    "contested_if": "vendor_count <= 2 or row_count < 5",
                    "status": "pending",
                }
            )

    if challenge == "related_parties":
        checks.append(
            {
                "finding_id": finding["finding_id"],
                "question": "Is this relationship based on a name-only match?",
                "sql": None,
                "contested_if": "no person identifier present",
                "status": "contested",
                "result": [{"matching_basis": "name_only"}],
                "interpretation": "Name-only related-party leads require identity validation before escalation.",
            }
        )

    return checks


def codex_check_plan(findings: list[dict[str, Any]], plan: dict[str, Any]) -> list[dict[str, Any]]:
    schema = read_json(paths.state_dir() / "discovered.schema.json", [])
    prompt = f"""
You are the disconfirming-check brain for LemonClaw, a public-interest accountability story engine.

Return JSON only. Do not use markdown.

Given findings, a schema profile, and the investigation plan, propose at most one SELECT/WITH SQL check per finding that could weaken or contextualize the finding. If no safe SQL check is possible, return a non_sql check with status "contested" or "inconclusive".

Rules:
- Never write SQL that mutates data.
- Use only table and column names visible in the schema or plan.
- Output small aggregate queries only.
- Do not accuse anyone.

Output shape:
{{"checks":[{{"finding_id":"...","question":"...","sql":"SELECT ... or null","contested_if":"...","status":"pending|contested|inconclusive","interpretation":"..."}}]}}

Findings:
{json.dumps(findings, indent=2)}

Plan:
{json.dumps(plan, indent=2)}

Schema:
{json.dumps(schema, indent=2)}
"""
    data = brain.codex_json(prompt)
    return data.get("checks", [])


def run_checks(checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    con = dataset.connect()
    out = []
    for check in checks:
        check = dict(check)
        sql = check.get("sql")
        if sql:
            try:
                safe = _safe_sql(sql)
                rows = records(con, safe)
                check["result"] = rows[:10]
                check["status"] = interpret_check(check, rows)
            except Exception as exc:
                check["status"] = "inconclusive"
                check["error"] = str(exc)
        out.append(check)
    return out


def interpret_check(check: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    finding_id = str(check.get("finding_id", ""))
    if finding_id.startswith("related_parties:"):
        return "contested"
    if not rows:
        return "inconclusive"
    row = rows[0]
    contested_if = str(check.get("contested_if", ""))
    if finding_id.startswith("amendment_creep:"):
        magnitude_values = [
            value
            for key, value in row.items()
            if (key.endswith("_multiple") or key.endswith("_delta")) and value is not None
        ]
        peer_counts = [
            value
            for key, value in row.items()
            if ("count_with_multiple_ge" in key or "count_with_delta_ge" in key) and value is not None
        ]
        try:
            if peer_counts and max(int(value) for value in peer_counts) > 1:
                return "contested"
            if magnitude_values and max(float(value) for value in magnitude_values) > 0:
                return "supported"
        except Exception:
            return "inconclusive"
    if finding_id.startswith("vendor_concentration:") and "distinct_vendors" in row and "row_count" in row:
        try:
            return "contested" if int(row.get("distinct_vendors", 0)) <= 2 or int(row.get("row_count", 0)) < 5 else "supported"
        except Exception:
            return "inconclusive"
    if finding_id.startswith("vendor_concentration:") and "row_count" in row:
        try:
            max_contract_share = row.get("max_contract_share_of_category")
            if max_contract_share is not None and float(max_contract_share) >= 0.5:
                return "contested"
            return "contested" if int(row.get("row_count", 0)) < 5 else "supported"
        except Exception:
            return "inconclusive"
    if "distinct_original_values" in row and "distinct_current_values" in row:
        try:
            row_count = int(row.get("row_count", 0))
            original_count = int(row.get("distinct_original_values", 0))
            current_count = int(row.get("distinct_current_values", 0))
            return "contested" if row_count > 1 and (original_count > 1 or current_count > 1) else "supported"
        except Exception:
            return "inconclusive"
    if "distinct_vendors" in row and "min_original_value" in row and "max_current_value" in row:
        try:
            row_count = int(row.get("row_count", 0))
            distinct_counts = [
                int(row.get("distinct_vendors", 0)),
                int(row.get("distinct_departments", 0)),
                int(row.get("distinct_categories", 0)),
                int(row.get("distinct_directors", 0)),
            ]
            mixed_values = row.get("min_original_value") != row.get("max_original_value") or row.get("min_current_value") != row.get("max_current_value")
            return "contested" if row_count > 1 and (mixed_values or any(value > 1 for value in distinct_counts)) else "supported"
        except Exception:
            return "inconclusive"
    if "absolute_increase" in row and "multiple" in row:
        try:
            return "supported" if int(row.get("row_count", 0)) == 1 and float(row.get("absolute_increase", 0)) > 0 else "contested"
        except Exception:
            return "inconclusive"
    if "category_row_count" in row:
        try:
            return "contested" if int(row.get("category_row_count", 0)) < 5 else "supported"
        except Exception:
            return "inconclusive"
    if "share_excluding_top_contract" in row:
        share = row.get("share_excluding_top_contract")
        if share is None:
            return "contested"
        try:
            return "contested" if float(share) < 0.6 else "supported"
        except Exception:
            return "inconclusive"
    if "p95_multiple" in row and "finding_multiple" in contested_if:
        try:
            marker = contested_if.split("finding_multiple (", 1)[1].split(")", 1)[0]
            return "contested" if float(row["p95_multiple"]) >= float(marker) else "supported"
        except Exception:
            return "inconclusive"
    if "vendor_count" in row:
        try:
            return "contested" if int(row["vendor_count"]) <= 2 or int(row.get("row_count", 0)) < 5 else "supported"
        except Exception:
            return "inconclusive"
    return "inconclusive"


def apply_checks(findings: list[dict[str, Any]], checks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for check in checks:
        by_id.setdefault(str(check.get("finding_id")), []).append(check)

    updated = []
    for finding in findings:
        finding = dict(finding)
        finding_checks = by_id.get(str(finding.get("finding_id")), [])
        statuses = {check.get("status") for check in finding_checks}
        if "contested" in statuses:
            support_status = "contested"
        elif "supported" in statuses:
            support_status = "supported"
        elif finding_checks:
            support_status = "inconclusive"
        else:
            support_status = "not_checked"
        finding["disconfirming_checks"] = finding_checks
        finding["support_status"] = support_status
        updated.append(finding)
    return updated


def disconfirm(brain_name: str = "heuristic") -> dict[str, Any]:
    plan = load_plan()
    verified_doc = read_json(paths.findings_dir() / "verified.json", None)
    if verified_doc:
        findings = verified_doc.get("findings", [])
    else:
        findings = ledger.load_all_findings()

    if brain_name == "codex":
        proposed = codex_check_plan(findings, plan)
    elif brain_name == "heuristic":
        proposed = [check for finding in findings for check in heuristic_checks_for_finding(finding, plan)]
    else:
        raise ValueError(f"unsupported disconfirm brain: {brain_name}")

    checks = run_checks(proposed)
    updated = apply_checks(findings, checks)
    out = {
        "generated_at": now_iso(),
        "brain": brain_name,
        "checks": checks,
        "summary": {
            "total": len(checks),
            "supported": sum(1 for c in checks if c.get("status") == "supported"),
            "contested": sum(1 for c in checks if c.get("status") == "contested"),
            "inconclusive": sum(1 for c in checks if c.get("status") == "inconclusive"),
        },
    }
    write_json(paths.findings_dir() / "disconfirming-checks.json", out)
    write_json(paths.findings_dir() / "verified.json", {"generated_at": now_iso(), "count": len(updated), "findings": updated})
    ledger.event("disconfirming_checks_completed", out["summary"])
    return out
