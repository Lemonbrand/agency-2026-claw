from __future__ import annotations

import os
from typing import Any

from . import dataset, ledger, paths
from .duck import records
from .jsonio import read_json
from .util import first_match, now_iso, quote_ident, slug

VENDOR_COLS = ["vendor_name", "supplier_name", "vendor", "supplier", "contractor", "organization_name"]
AMOUNT_COLS = ["current_value", "contract_value", "total_value", "award_amount", "amount", "value"]
CATEGORY_COLS = ["category", "commodity", "service", "department", "program", "buyer"]
ORIGINAL_COLS = ["original_value", "initial_value", "original_amount", "initial_amount", "award_amount"]
CURRENT_COLS = ["current_value", "amended_value", "revised_value", "total_value", "contract_value"]
PERSON_COLS = ["director_name", "officer_name", "person_name", "principal_name", "board_member", "contact_name"]
ORG_COLS = ["recipient_name", "charity_name", "organization_name", "vendor_name", "supplier_name", "company_name"]


def _profiles() -> list[dict[str, Any]]:
    profiles = dataset.table_profiles()
    if not profiles:
        raise SystemExit("No schema profile. Run ./bin/agency onboard first.")
    return profiles


def _source_manifest_by_table() -> dict[str, dict[str, Any]]:
    manifest = read_json(paths.state_dir() / "dataset-manifest.json", [])
    return {row["table"]: row for row in manifest}


def vendor_concentration(limit: int = 20) -> list[dict[str, Any]]:
    threshold = float(os.environ.get("VENDOR_CONCENTRATION_THRESHOLD", "0.60"))
    con = dataset.connect()
    sources = _source_manifest_by_table()
    findings: list[dict[str, Any]] = []

    for profile in _profiles():
        table = profile["table"]
        cols = [c["name"] for c in profile["columns"]]
        vendor = first_match(cols, VENDOR_COLS)
        amount = first_match(cols, AMOUNT_COLS)
        category = first_match(cols, CATEGORY_COLS)
        if not vendor or not amount:
            continue

        group_expr = quote_ident(category) if category else "'all'"
        sql = f"""
WITH base AS (
  SELECT
    CAST({quote_ident(vendor)} AS VARCHAR) AS vendor,
    CAST({group_expr} AS VARCHAR) AS group_key,
    try_cast({quote_ident(amount)} AS DOUBLE) AS amount
  FROM {quote_ident(table)}
),
clean AS (
  SELECT * FROM base
  WHERE vendor IS NOT NULL AND amount IS NOT NULL AND amount > 0
),
shares AS (
  SELECT
    group_key,
    vendor,
    sum(amount) AS vendor_spend,
    count(*) AS row_count,
    sum(sum(amount)) OVER (PARTITION BY group_key) AS group_spend
  FROM clean
  GROUP BY group_key, vendor
),
ranked AS (
  SELECT *, vendor_spend / nullif(group_spend, 0) AS share,
    row_number() OVER (PARTITION BY group_key ORDER BY vendor_spend DESC) AS rank
  FROM shares
)
SELECT * FROM ranked
WHERE rank = 1 AND share >= {threshold}
ORDER BY share DESC, group_spend DESC
LIMIT {limit}
""".strip()
        rows = records(con, sql)
        for row in rows:
            entity = str(row["vendor"])
            findings.append(
                {
                    "finding_id": f"vendor_concentration:{slug(table)}:{slug(row['group_key'])}:{slug(entity)}",
                    "challenge": "vendor_concentration",
                    "entity": entity,
                    "entity_type": "vendor",
                    "story_type": "risk",
                    "lens": "concentration",
                    "claim": f"{entity} holds {row['share']:.1%} of spend in {row['group_key']}",
                    "severity": "medium" if row["share"] < 0.8 else "high",
                    "confidence": 0.86,
                    "status": "needs_human_review",
                    "generated_at": now_iso(),
                    "evidence": [
                        {
                            "table": table,
                            "source_file_sha256": sources.get(table, {}).get("source_sha256"),
                            "sql": sql,
                            "summary": f"Top vendor share {row['share']:.1%}; spend {row['vendor_spend']:.2f} of {row['group_spend']:.2f}.",
                            "metrics": row,
                        }
                    ],
                    "verification": {"replayed": False, "disconfirming_query_run": False},
                }
            )
    ledger.save_findings("vendor-concentration", findings)
    return findings


def amendment_creep(limit: int = 20) -> list[dict[str, Any]]:
    threshold = float(os.environ.get("AMENDMENT_CREEP_THRESHOLD", "3.0"))
    con = dataset.connect()
    sources = _source_manifest_by_table()
    findings: list[dict[str, Any]] = []

    for profile in _profiles():
        table = profile["table"]
        cols = [c["name"] for c in profile["columns"]]
        original = first_match(cols, ORIGINAL_COLS)
        current = first_match(cols, CURRENT_COLS)
        vendor = first_match(cols, VENDOR_COLS) or first_match(cols, ORG_COLS)
        contract = first_match(cols, ["contract_id", "contract_number", "id", "reference"])
        if not original or not current:
            continue

        vendor_expr = quote_ident(vendor) if vendor else "'unknown vendor'"
        contract_expr = quote_ident(contract) if contract else "'unknown contract'"
        sql = f"""
SELECT
  CAST({contract_expr} AS VARCHAR) AS contract_ref,
  CAST({vendor_expr} AS VARCHAR) AS vendor,
  try_cast({quote_ident(original)} AS DOUBLE) AS original_value,
  try_cast({quote_ident(current)} AS DOUBLE) AS current_value,
  try_cast({quote_ident(current)} AS DOUBLE) / nullif(try_cast({quote_ident(original)} AS DOUBLE), 0) AS multiple
FROM {quote_ident(table)}
WHERE try_cast({quote_ident(original)} AS DOUBLE) > 0
  AND try_cast({quote_ident(current)} AS DOUBLE) / nullif(try_cast({quote_ident(original)} AS DOUBLE), 0) >= {threshold}
ORDER BY multiple DESC
LIMIT {limit}
""".strip()
        rows = records(con, sql)
        for row in rows:
            entity = str(row["vendor"])
            findings.append(
                {
                    "finding_id": f"amendment_creep:{slug(table)}:{slug(row['contract_ref'])}",
                    "challenge": "amendment_creep",
                    "entity": entity,
                    "entity_type": "vendor",
                    "story_type": "risk",
                    "lens": "post_award_growth",
                    "claim": f"Contract {row['contract_ref']} increased {row['multiple']:.1f}x after award",
                    "severity": "high" if row["multiple"] >= threshold * 2 else "medium",
                    "confidence": 0.9,
                    "status": "needs_human_review",
                    "generated_at": now_iso(),
                    "evidence": [
                        {
                            "table": table,
                            "source_file_sha256": sources.get(table, {}).get("source_sha256"),
                            "sql": sql,
                            "summary": f"Original {row['original_value']:.2f}; current {row['current_value']:.2f}; multiple {row['multiple']:.1f}x.",
                            "metrics": row,
                        }
                    ],
                    "verification": {"replayed": False, "disconfirming_query_run": False},
                }
            )
    ledger.save_findings("amendment-creep", findings)
    return findings


def related_parties(limit: int = 20) -> list[dict[str, Any]]:
    min_orgs = int(os.environ.get("RELATED_PARTY_MIN_ORGS", "2"))
    con = dataset.connect()
    sources = _source_manifest_by_table()
    selects: list[str] = []
    source_tables: list[str] = []

    for profile in _profiles():
        table = profile["table"]
        cols = [c["name"] for c in profile["columns"]]
        person = first_match(cols, PERSON_COLS)
        org = first_match(cols, ORG_COLS)
        if not person or not org:
            continue
        selects.append(
            f"SELECT '{table}' AS source_table, CAST({quote_ident(person)} AS VARCHAR) AS person, CAST({quote_ident(org)} AS VARCHAR) AS org FROM {quote_ident(table)}"
        )
        source_tables.append(table)

    findings: list[dict[str, Any]] = []
    if not selects:
        ledger.save_findings("related-parties", findings)
        return findings

    sql = f"""
WITH links AS (
  {' UNION ALL '.join(selects)}
),
clean AS (
  SELECT source_table, trim(person) AS person, trim(org) AS org
  FROM links
  WHERE person IS NOT NULL AND org IS NOT NULL AND trim(person) != '' AND trim(org) != ''
),
ranked AS (
  SELECT
    person,
    count(DISTINCT org) AS org_count,
    string_agg(DISTINCT org, ' | ') AS orgs,
    string_agg(DISTINCT source_table, ' | ') AS source_tables
  FROM clean
  GROUP BY person
)
SELECT *
FROM ranked
WHERE org_count >= {min_orgs}
ORDER BY org_count DESC, person
LIMIT {limit}
""".strip()

    rows = records(con, sql)
    source_hashes = {table: sources.get(table, {}).get("source_sha256") for table in source_tables}
    for row in rows:
        person = str(row["person"])
        findings.append(
            {
                "finding_id": f"related_parties:{slug(person)}",
                "challenge": "related_parties",
                "entity": person,
                "entity_type": "person",
                "story_type": "operating_insight",
                "lens": "name_overlap_review",
                "claim": f"{person} appears across {row['org_count']} organizations in the loaded data",
                "severity": "medium",
                "confidence": 0.72,
                "status": "needs_human_review",
                "generated_at": now_iso(),
                "evidence": [
                    {
                        "table": "multi_table_person_org_links",
                        "source_file_sha256": source_hashes,
                        "sql": sql,
                        "summary": f"Person connected to: {row['orgs']}",
                        "metrics": row,
                    }
                ],
                "verification": {"replayed": False, "disconfirming_query_run": False},
            }
        )
    ledger.save_findings("related-parties", findings)
    return findings
