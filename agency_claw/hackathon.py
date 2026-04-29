"""LemonClaw hackathon path: query the GovAlta Postgres directly via DuckDB.

Materializes a working subset of the four schemas (cra, fed, ab, general) into
local DuckDB tables prefixed `hk_`, then runs hackathon-specific detectors
against them. Findings carry the same shape as detectors.py so the rest of the
pipeline (verify, disconfirm, resolve, correlate, review, dashboard, promote)
runs unchanged.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import duckdb

from . import dataset, ledger, paths
from .jsonio import write_json
from .util import now_iso, slug


def pg_url() -> str:
    url = os.environ.get("HACKATHON_PG")
    if not url:
        raise SystemExit(
            "HACKATHON_PG env var not set. Copy .env.example to .env and source ./scripts/bootstrap.sh."
        )
    return url


def attach(con: duckdb.DuckDBPyConnection) -> None:
    con.execute("SET enable_progress_bar = false")
    con.execute("INSTALL postgres; LOAD postgres;")
    try:
        con.execute("DETACH pg")
    except duckdb.Error:
        pass
    con.execute(f"ATTACH '{pg_url()}' AS pg (TYPE postgres, READ_ONLY)")


def materialize(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Pull a working subset locally so the demo path is offline-resilient."""
    manifest: list[dict[str, Any]] = []
    started = time.time()

    moves = [
        # Cross-jurisdictional gold: every entity with at least one source link.
        (
            "hk_golden",
            """
            SELECT
              id AS golden_id, canonical_name, entity_type, bn_root,
              source_link_count, dataset_sources,
              cra_profile, fed_profile, ab_profile,
              CAST(cra_profile IS NOT NULL AS INTEGER)
                + CAST(fed_profile IS NOT NULL AS INTEGER)
                + CAST(ab_profile IS NOT NULL AS INTEGER) AS jurisdiction_count,
              COALESCE(CAST(fed_profile->>'total_grants' AS DOUBLE), 0) AS fed_total,
              COALESCE(CAST(fed_profile->>'grant_count' AS INTEGER), 0) AS fed_count,
              COALESCE(CAST(ab_profile->>'total_grants' AS DOUBLE), 0) AS ab_total,
              COALESCE(CAST(ab_profile->>'payment_count' AS INTEGER), 0) AS ab_count
            FROM pg.general.entity_golden_records
            WHERE source_link_count > 0
            """,
        ),
        # Pre-computed circular-gifting universe with score 0-30.
        (
            "hk_loops",
            """
            SELECT bn, legal_name, score, total_circular_amt, total_loops,
                   loops_2hop, loops_3hop, loops_4hop, loops_5hop, loops_6hop, loops_7plus,
                   max_bottleneck
            FROM pg.cra.loop_universe
            """,
        ),
        # Alberta sole-source contracts (15K rows; small).
        (
            "hk_sole_source",
            """
            SELECT id, vendor, amount, ministry, contract_services,
                   permitted_situations, special, start_date, end_date,
                   display_fiscal_year
            FROM pg.ab.ab_sole_source
            """,
        ),
        # Federal grants rolled up to (recipient, owner_org_title, ref_number) latest amendment.
        # Implements F-3 mitigation: pick the latest amendment per agreement key.
        (
            "hk_fed_current",
            """
            WITH ranked AS (
              SELECT
                ref_number,
                COALESCE(recipient_business_number, recipient_legal_name) AS recipient_key,
                recipient_legal_name,
                recipient_business_number,
                owner_org_title,
                prog_name_en,
                agreement_value,
                agreement_start_date,
                agreement_end_date,
                amendment_date,
                amendment_number,
                is_amendment,
                ROW_NUMBER() OVER (
                  PARTITION BY ref_number,
                               COALESCE(recipient_business_number, recipient_legal_name)
                  ORDER BY COALESCE(amendment_date, agreement_start_date) DESC NULLS LAST,
                           CAST(amendment_number AS VARCHAR) DESC NULLS LAST
                ) AS rn
              FROM pg.fed.grants_contributions
              WHERE ref_number IS NOT NULL
                AND agreement_value IS NOT NULL
                AND agreement_value > 0
            )
            SELECT * FROM ranked WHERE rn = 1
            """,
        ),
        # FED originals: is_amendment = false, joined on the same key for amendment-creep.
        (
            "hk_fed_originals",
            """
            SELECT
              ref_number,
              COALESCE(recipient_business_number, recipient_legal_name) AS recipient_key,
              recipient_legal_name,
              owner_org_title,
              agreement_value AS original_value,
              agreement_start_date
            FROM pg.fed.grants_contributions
            WHERE is_amendment = false
              AND agreement_value IS NOT NULL
              AND agreement_value > 0
              AND ref_number IS NOT NULL
            """,
        ),
        # CRA shared-director candidates: directors that appear under 2+ BNs.
        (
            "hk_shared_directors",
            """
            WITH per_person AS (
              SELECT
                trim(first_name) || ' ' || trim(last_name) AS person,
                bn,
                COUNT(*) AS rows
              FROM pg.cra.cra_directors
              WHERE first_name IS NOT NULL AND last_name IS NOT NULL
                AND trim(first_name) <> '' AND trim(last_name) <> ''
              GROUP BY ALL
            )
            SELECT person,
                   COUNT(DISTINCT bn) AS bn_count,
                   string_agg(DISTINCT bn, ', ') AS bns
            FROM per_person
            GROUP BY person
            HAVING COUNT(DISTINCT bn) >= 3
            """,
        ),
    ]

    for table, sql in moves:
        t0 = time.time()
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(f"CREATE TABLE {table} AS {sql}")
        n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
        elapsed = time.time() - t0
        manifest.append(
            {
                "table": table,
                "row_count": n,
                "elapsed_s": round(elapsed, 1),
                "source_schema": "postgres",
                "source_sha256": None,
                "source_name": "pg_attach",
            }
        )
        print(f"  materialized {table}: {n:,} rows ({elapsed:.1f}s)")

    print(f"total: {time.time() - started:.1f}s")
    return {"manifest": manifest, "started_at": now_iso()}


def profile_local_tables(con: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    """Profile the materialized hk_* tables for the planner's applicability matrix."""
    profiles: list[dict[str, Any]] = []
    rows = con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'hk_%' ORDER BY table_name"
    ).fetchall()
    for (table,) in rows:
        info = con.execute(f'PRAGMA table_info("{table}")').fetchall()
        columns = [{"name": row[1], "type": row[2]} for row in info]
        col_names = [c["name"] for c in columns]
        row_count = con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
        sample_rows = con.execute(f'SELECT * FROM "{table}" LIMIT 3').fetchall()
        sample = [dict(zip(col_names, row)) for row in sample_rows]
        sample = json.loads(json.dumps(sample, default=str))
        profiles.append(
            {
                "table": table,
                "row_count": row_count,
                "columns": columns,
                "nulls": {},
                "sample": sample,
            }
        )
    return profiles


def onboard() -> dict[str, Any]:
    """Attach Postgres, materialize subsets, write manifest + schema profile."""
    paths.ensure_dirs()
    con = dataset.connect()
    attach(con)
    print("attached pg, materializing subsets...")
    out = materialize(con)
    profiles = profile_local_tables(con)

    write_json(paths.state_dir() / "dataset-manifest.json", out["manifest"])
    write_json(paths.state_dir() / "discovered.schema.json", profiles)
    ledger.event(
        "hackathon_onboard",
        {"tables": [row["table"] for row in out["manifest"]], "started_at": out["started_at"]},
    )
    return {"manifest": out["manifest"], "profiles": profiles}


# ---------------------------------------------------------------------------
# Detectors
# ---------------------------------------------------------------------------


def _evidence(table: str, sql: str, summary: str, metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "table": table,
        "source_file_sha256": None,
        "sql": sql,
        "summary": summary,
        "metrics": metrics,
    }


def _records(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict[str, Any]]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def detect_tri_jurisdictional(limit: int = 25) -> list[dict[str, Any]]:
    """Find entities funded by CRA + FED + AB simultaneously."""
    con = dataset.connect()
    min_fed = float(os.environ.get("TRI_JURIS_MIN_FED_CAD", "10000"))
    min_ab = float(os.environ.get("TRI_JURIS_MIN_AB_CAD", "10000"))

    sql = f"""
    SELECT canonical_name, entity_type, bn_root, source_link_count,
           fed_total, fed_count, ab_total, ab_count, dataset_sources
    FROM hk_golden
    WHERE jurisdiction_count = 3
      AND fed_total >= {min_fed}
      AND ab_total >= {min_ab}
    ORDER BY (fed_total + ab_total) DESC
    LIMIT {limit}
    """
    rows = _records(con, sql)

    findings: list[dict[str, Any]] = []
    for row in rows:
        entity = str(row["canonical_name"])
        bn = str(row.get("bn_root") or "")
        fed = float(row.get("fed_total") or 0)
        ab = float(row.get("ab_total") or 0)
        findings.append(
            {
                "finding_id": f"tri_jurisdictional:{slug(entity)}:{bn}",
                "challenge": "tri_jurisdictional_funding",
                "entity": entity,
                "entity_type": "organization",
                "story_type": "policy_gap",
                "lens": "uncoordinated_overlap",
                "claim": (
                    f"{entity} (BN {bn}) appears in CRA, federal, and Alberta records: "
                    f"${fed:,.0f} federal across {row.get('fed_count')} grants, "
                    f"${ab:,.0f} Alberta across {row.get('ab_count')} payments."
                ),
                "severity": "medium",
                "confidence": 0.92,
                "status": "needs_human_review",
                "generated_at": now_iso(),
                "evidence": [
                    _evidence(
                        "hk_golden",
                        sql.strip(),
                        f"Tri-jurisdictional entity, ${fed + ab:,.0f} combined federal+Alberta funding.",
                        json.loads(json.dumps(row, default=str)),
                    )
                ],
                "verification": {"replayed": False, "disconfirming_query_run": False},
            }
        )

    ledger.save_findings("tri-jurisdictional-funding", findings)
    return findings


def detect_funding_loops(limit: int = 25) -> list[dict[str, Any]]:
    """Wrap CRA's pre-computed circular-gifting risk score (0-30)."""
    con = dataset.connect()
    min_score = int(os.environ.get("FUNDING_LOOP_MIN_SCORE", "10"))

    sql = f"""
    SELECT bn, legal_name, score, total_circular_amt, total_loops,
           loops_2hop, loops_3hop, loops_4hop, loops_5hop, loops_6hop, loops_7plus,
           max_bottleneck
    FROM hk_loops
    WHERE score >= {min_score}
    ORDER BY score DESC, total_circular_amt DESC
    LIMIT {limit}
    """
    rows = _records(con, sql)

    findings: list[dict[str, Any]] = []
    for row in rows:
        entity = str(row.get("legal_name") or row.get("bn"))
        score = int(row["score"])
        amount = float(row.get("total_circular_amt") or 0)
        loops = int(row.get("total_loops") or 0)
        findings.append(
            {
                "finding_id": f"funding_loops:{slug(str(row['bn']))}",
                "challenge": "funding_loops",
                "entity": entity,
                "entity_type": "charity",
                "story_type": "risk",
                "lens": "circular_transfer",
                "claim": (
                    f"{entity} sits in {loops} qualified-donee gift loops with a CRA risk score of "
                    f"{score}/30 and ${amount:,.0f} in circular gift volume."
                ),
                "severity": "high" if score >= 20 else "medium",
                "confidence": 0.95,
                "status": "needs_human_review",
                "generated_at": now_iso(),
                "evidence": [
                    _evidence(
                        "hk_loops",
                        sql.strip(),
                        f"CRA loop risk score {score}/30; {loops} loops; ${amount:,.0f} circular volume.",
                        json.loads(json.dumps(row, default=str)),
                    )
                ],
                "verification": {"replayed": False, "disconfirming_query_run": False},
            }
        )

    ledger.save_findings("funding-loops", findings)
    return findings


def detect_sole_source_concentration(limit: int = 25) -> list[dict[str, Any]]:
    """Vendor concentration on Alberta sole-source contracts, by ministry."""
    con = dataset.connect()
    threshold = float(os.environ.get("SOLE_SOURCE_THRESHOLD", "0.55"))

    sql = f"""
    WITH base AS (
      SELECT vendor, ministry, amount
      FROM hk_sole_source
      WHERE vendor IS NOT NULL AND amount IS NOT NULL AND amount > 0
    ),
    shares AS (
      SELECT ministry, vendor,
             SUM(amount) AS vendor_spend,
             COUNT(*) AS row_count,
             SUM(SUM(amount)) OVER (PARTITION BY ministry) AS ministry_spend
      FROM base
      GROUP BY ministry, vendor
    ),
    ranked AS (
      SELECT *,
             vendor_spend / NULLIF(ministry_spend, 0) AS share,
             ROW_NUMBER() OVER (PARTITION BY ministry ORDER BY vendor_spend DESC) AS rn,
             COUNT(*) OVER (PARTITION BY ministry) AS vendor_count
      FROM shares
    )
    SELECT vendor, ministry, vendor_spend, ministry_spend, share, vendor_count
    FROM ranked
    WHERE rn = 1 AND share >= {threshold} AND vendor_count >= 3
    ORDER BY share DESC, ministry_spend DESC
    LIMIT {limit}
    """
    rows = _records(con, sql)

    findings: list[dict[str, Any]] = []
    for row in rows:
        vendor = str(row["vendor"])
        ministry = str(row["ministry"])
        share = float(row["share"])
        spend = float(row.get("ministry_spend") or 0)
        findings.append(
            {
                "finding_id": f"sole_source_concentration:{slug(ministry)}:{slug(vendor)}",
                "challenge": "sole_source_concentration",
                "entity": vendor,
                "entity_type": "vendor",
                "story_type": "risk",
                "lens": "sole_source_dominance",
                "claim": (
                    f"{vendor} holds {share:.1%} of {ministry}'s sole-source spend "
                    f"(${spend:,.0f} total in this ministry's sole-source contracts)."
                ),
                "severity": "high" if share >= 0.8 else "medium",
                "confidence": 0.88,
                "status": "needs_human_review",
                "generated_at": now_iso(),
                "evidence": [
                    _evidence(
                        "hk_sole_source",
                        sql.strip(),
                        f"Top sole-source vendor share {share:.1%} of ${spend:,.0f} in {ministry}.",
                        json.loads(json.dumps(row, default=str)),
                    )
                ],
                "verification": {"replayed": False, "disconfirming_query_run": False},
            }
        )

    ledger.save_findings("sole-source-concentration", findings)
    return findings


def detect_amendment_creep_fed(limit: int = 25) -> list[dict[str, Any]]:
    """Federal contracts whose current value materially exceeds the original.

    Uses the F-3-safe deduplication: latest amendment per (ref_number, recipient_key).
    """
    con = dataset.connect()
    threshold = float(os.environ.get("AMENDMENT_CREEP_THRESHOLD", "3.0"))

    sql = f"""
    WITH joined AS (
      SELECT c.ref_number,
             c.recipient_legal_name AS recipient,
             c.owner_org_title AS department,
             c.prog_name_en AS program,
             o.original_value,
             c.agreement_value AS current_value,
             c.agreement_value / NULLIF(o.original_value, 0) AS multiple
      FROM hk_fed_current c
      JOIN hk_fed_originals o
        ON o.ref_number = c.ref_number
       AND o.recipient_key = c.recipient_key
      WHERE o.original_value > 0
    )
    SELECT *
    FROM joined
    WHERE multiple >= {threshold}
    ORDER BY multiple DESC, current_value DESC
    LIMIT {limit}
    """
    rows = _records(con, sql)

    findings: list[dict[str, Any]] = []
    for row in rows:
        recipient = str(row["recipient"])
        ref = str(row["ref_number"])
        multiple = float(row["multiple"])
        original = float(row["original_value"])
        current = float(row["current_value"])
        findings.append(
            {
                "finding_id": f"amendment_creep_fed:{slug(ref)}:{slug(recipient)}",
                "challenge": "amendment_creep",
                "entity": recipient,
                "entity_type": "vendor",
                "story_type": "risk",
                "lens": "post_award_growth",
                "claim": (
                    f"Federal agreement {ref} to {recipient} ({row.get('department')}) grew "
                    f"{multiple:.1f}x: ${original:,.0f} -> ${current:,.0f}."
                ),
                "severity": "high" if multiple >= threshold * 2 else "medium",
                "confidence": 0.9,
                "status": "needs_human_review",
                "generated_at": now_iso(),
                "evidence": [
                    _evidence(
                        "hk_fed_current+hk_fed_originals",
                        sql.strip(),
                        f"Original ${original:,.0f}; current ${current:,.0f}; multiple {multiple:.1f}x.",
                        json.loads(json.dumps(row, default=str)),
                    )
                ],
                "verification": {"replayed": False, "disconfirming_query_run": False},
            }
        )

    ledger.save_findings("amendment-creep-fed", findings)
    return findings


def detect_shared_directors(limit: int = 25) -> list[dict[str, Any]]:
    """Directors appearing on the boards of 3+ distinct charities."""
    con = dataset.connect()
    sql = f"""
    SELECT person, bn_count, bns
    FROM hk_shared_directors
    ORDER BY bn_count DESC, person
    LIMIT {limit}
    """
    rows = _records(con, sql)

    findings: list[dict[str, Any]] = []
    for row in rows:
        person = str(row["person"])
        count = int(row["bn_count"])
        findings.append(
            {
                "finding_id": f"shared_directors:{slug(person)}",
                "challenge": "related_parties",
                "entity": person,
                "entity_type": "person",
                "story_type": "operating_insight",
                "lens": "name_overlap_review",
                "claim": (
                    f"The name '{person}' appears on the boards of {count} distinct charities "
                    "(by BN). Identity validation required before any governance claim."
                ),
                "severity": "medium",
                "confidence": 0.65,
                "status": "needs_human_review",
                "generated_at": now_iso(),
                "evidence": [
                    _evidence(
                        "hk_shared_directors",
                        sql.strip(),
                        f"Name appears across {count} charity BNs.",
                        json.loads(json.dumps(row, default=str)),
                    )
                ],
                "verification": {"replayed": False, "disconfirming_query_run": False},
            }
        )

    ledger.save_findings("shared-directors", findings)
    return findings


DETECTORS = {
    "tri-jurisdictional-funding": detect_tri_jurisdictional,
    "funding-loops": detect_funding_loops,
    "sole-source-concentration": detect_sole_source_concentration,
    "amendment-creep-fed": detect_amendment_creep_fed,
    "shared-directors": detect_shared_directors,
}


def run_all(limit: int = 25) -> dict[str, Any]:
    runs = []
    for name, fn in DETECTORS.items():
        findings = fn(limit=limit)
        runs.append({"skill": name, "finding_count": len(findings)})
        print(f"  {name}: {len(findings)} findings")
        ledger.event("hackathon_skill_run", {"skill": name, "count": len(findings)})
    return {"runs": runs}
