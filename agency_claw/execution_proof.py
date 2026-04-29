from __future__ import annotations

from typing import Any

from . import directdb, ledger, paths
from .challenge_contract import CHALLENGES, Challenge
from .jsonio import write_json
from .util import now_iso


PROBES: dict[int, dict[str, Any]] = {
    1: {
        "name": "stale-filing high-government-share cohort",
        "proof_level": "sql-executed-review-lead",
        "missing": ["legal dissolution date", "bankruptcy date", "revocation reason"],
        "sql": """
WITH latest AS (
  SELECT bn, max(fiscal_year) AS latest_filing_year
  FROM pg.cra.cra_identification
  GROUP BY bn
),
max_year AS (
  SELECT max(fiscal_year) AS max_filing_year FROM pg.cra.cra_identification
),
high_gov AS (
  SELECT bn, max(legal_name) AS legal_name,
         max(govt_share_of_rev) AS max_gov_share,
         sum(total_govt) AS total_govt_reported
  FROM pg.cra.govt_funding_by_charity
  WHERE govt_share_of_rev >= 70
  GROUP BY bn
),
candidates AS (
  SELECT high_gov.legal_name, high_gov.bn, latest.latest_filing_year,
         high_gov.max_gov_share, high_gov.total_govt_reported
  FROM high_gov
  JOIN latest ON latest.bn = high_gov.bn
  JOIN max_year ON true
  WHERE latest.latest_filing_year <= max_year.max_filing_year - 2
    AND high_gov.total_govt_reported >= 100000
)
SELECT *
FROM candidates
LIMIT 10
""",
    },
    2: {
        "name": "persistent thin delivery-capacity signal",
        "proof_level": "sql-executed-review-lead",
        "missing": ["exact employee headcount", "verified physical-presence classification"],
        "sql": """
WITH yearly AS (
  SELECT g.bn, g.legal_name, g.fiscal_year, g.govt_share_of_rev,
         g.total_govt, g.revenue
  FROM pg.cra.govt_funding_by_charity g
  WHERE g.revenue > 0
    AND g.govt_share_of_rev >= 70
    AND lower(g.legal_name) NOT LIKE '%hospital%'
    AND lower(g.legal_name) NOT LIKE '%school%'
    AND lower(g.legal_name) NOT LIKE '%health authority%'
    AND lower(g.legal_name) NOT LIKE '%university%'
    AND lower(g.legal_name) NOT LIKE '%college%'
),
scored AS (
  SELECT bn, max(legal_name) AS legal_name,
         count(*) AS years_seen,
         avg(govt_share_of_rev) AS avg_gov_share,
         sum(total_govt) AS total_govt,
         sum(revenue) AS total_revenue
  FROM yearly
  GROUP BY bn
)
SELECT *
FROM scored
WHERE years_seen >= 3
  AND avg_gov_share >= 70
LIMIT 10
""",
    },
    3: {
        "name": "top CRA circular-gift loop scores",
        "proof_level": "sql-executed",
        "missing": ["manual classification for denominational or federated structures"],
        "sql": """
SELECT bn, legal_name, score, total_loops, total_circular_amt,
       loops_2hop, loops_3hop, loops_4hop, loops_5hop, loops_6hop, loops_7plus,
       count(*) OVER () AS scored_charities
FROM pg.cra.loop_universe
WHERE score >= 10
ORDER BY score DESC, total_circular_amt DESC NULLS LAST
LIMIT 10
""",
    },
    4: {
        "name": "federal amendment creep and Alberta sole-source concentration",
        "proof_level": "sql-executed-partial",
        "missing": ["bidder counts", "losing bids", "full procurement method history"],
        "sql": """
WITH vendor_ministry AS (
  SELECT ministry, vendor,
         count(*) AS sole_source_count,
         sum(amount) AS vendor_spend,
         min(start_date) AS first_start,
         max(start_date) AS last_start
  FROM pg.ab.ab_sole_source
  WHERE vendor IS NOT NULL AND ministry IS NOT NULL AND amount > 0
  GROUP BY ministry, vendor
),
shares AS (
  SELECT *,
         sum(vendor_spend) OVER (PARTITION BY ministry) AS ministry_spend,
         vendor_spend / NULLIF(sum(vendor_spend) OVER (PARTITION BY ministry), 0) AS share
  FROM vendor_ministry
)
SELECT *, count(*) OVER () AS cohort_size
FROM shares
WHERE share >= 0.50
ORDER BY share DESC, vendor_spend DESC
LIMIT 10
""",
    },
    5: {
        "name": "Alberta sole-source ministry HHI",
        "proof_level": "sql-executed",
        "missing": ["statutory monopoly context", "supplier-market denominator"],
        "sql": """
WITH base AS (
  SELECT ministry, vendor, sum(amount) AS vendor_spend
  FROM pg.ab.ab_sole_source
  WHERE amount > 0 AND vendor IS NOT NULL AND ministry IS NOT NULL
  GROUP BY ministry, vendor
),
shares AS (
  SELECT ministry, vendor, vendor_spend,
         sum(vendor_spend) OVER (PARTITION BY ministry) AS ministry_spend,
         vendor_spend / NULLIF(sum(vendor_spend) OVER (PARTITION BY ministry), 0) AS share
  FROM base
),
hhi AS (
  SELECT ministry,
         count(*) AS vendor_count,
         sum(vendor_spend) AS ministry_spend,
         sum(share * share) AS hhi,
         max(share) AS top_share
  FROM shares
  GROUP BY ministry
),
ranked AS (
  SELECT ministry, vendor, vendor_spend,
         row_number() OVER (PARTITION BY ministry ORDER BY vendor_spend DESC) AS rn
  FROM shares
)
SELECT hhi.*, ranked.vendor AS top_vendor, ranked.vendor_spend AS top_vendor_spend,
       count(*) OVER () AS ministry_count
FROM hhi
LEFT JOIN ranked ON ranked.ministry = hhi.ministry AND ranked.rn = 1
WHERE hhi.vendor_count >= 3
ORDER BY hhi.hhi DESC, hhi.ministry_spend DESC
LIMIT 15
""",
    },
    6: {
        "name": "CRA director source sample for related-party materialization",
        "proof_level": "sql-executed-source-sample",
        "missing": ["durable person identifier", "corporate registry principal data"],
        "sql": """
SELECT bn, fpe, trim(first_name) || ' ' || trim(last_name) AS person,
       position, at_arms_length, start_date, end_date
FROM pg.cra.cra_directors
WHERE first_name IS NOT NULL
  AND last_name IS NOT NULL
  AND trim(first_name) <> ''
  AND trim(last_name) <> ''
LIMIT 10
""",
    },
    7: {
        "name": "broadband spend isolation for external policy comparison",
        "proof_level": "sql-executed-external-needed",
        "missing": ["policy commitment corpus", "target geography", "rural/urban classification"],
        "sql": """
SELECT owner_org_title, prog_name_en, agreement_value,
       agreement_start_date, agreement_end_date,
       recipient_legal_name
FROM pg.fed.grants_contributions
WHERE agreement_value IS NOT NULL AND agreement_value > 0
  AND owner_org_title IS NOT NULL
  AND prog_name_en IS NOT NULL
LIMIT 10
""",
    },
    8: {
        "name": "cross-jurisdiction funding overlap",
        "proof_level": "sql-executed-partial",
        "missing": ["same-purpose comparison", "eligible-cost categories", "policy-priority corpus for gaps"],
        "sql": """
SELECT canonical_name, bn_root,
       COALESCE((fed_profile->>'total_grants')::numeric, 0) AS fed_total_grants,
       COALESCE((fed_profile->>'grant_count')::numeric, 0) AS fed_grant_count,
       COALESCE((ab_profile->>'total_grants')::numeric, 0) AS ab_total_grants,
       COALESCE((ab_profile->>'payment_count')::numeric, 0) AS ab_grant_payment_count,
       source_link_count
FROM pg.general.entity_golden_records
WHERE fed_profile IS NOT NULL
  AND ab_profile IS NOT NULL
  AND bn_root IS NOT NULL
  AND COALESCE((fed_profile->>'total_grants')::numeric, 0) >= 10000
  AND COALESCE((ab_profile->>'total_grants')::numeric, 0) >= 10000
LIMIT 10
""",
    },
    9: {
        "name": "spend growth and vendor diversity over time",
        "proof_level": "sql-executed-partial",
        "missing": ["unit quantity", "deliverable count", "inflation deflator"],
        "sql": """
WITH yearly AS (
  SELECT display_fiscal_year AS year,
         ministry,
         contract_services,
         count(*) AS contract_count,
         count(DISTINCT vendor) AS vendor_count,
         sum(amount) AS spend,
         avg(amount) AS avg_contract_value
  FROM pg.ab.ab_sole_source
  WHERE amount > 0
    AND display_fiscal_year IS NOT NULL
    AND ministry IS NOT NULL
    AND contract_services IS NOT NULL
  GROUP BY display_fiscal_year, ministry, contract_services
)
SELECT *, count(*) OVER () AS cohort_size
FROM yearly
WHERE contract_count >= 3
ORDER BY spend DESC
LIMIT 15
""",
    },
    10: {
        "name": "internal flags for funded entities, not adverse media",
        "proof_level": "sql-executed-external-needed",
        "missing": ["regulatory enforcement sources", "court records", "serious adverse media citations"],
        "sql": """
SELECT bn, fpe, fiscal_year, legal_name, rule_code, rule_family, severity, details
FROM pg.cra.t3010_impossibilities
WHERE severity IS NOT NULL
LIMIT 10
""",
    },
}


def proof_status(challenge: Challenge, result: dict[str, Any], missing: list[str]) -> str:
    if not result.get("ok"):
        return "execution_failed"
    if challenge.status_default == "NEEDS_EXTERNAL_DATA":
        return "external_needed_after_internal_probe"
    if missing:
        return "executed_with_known_roadblocks"
    return "executed"


def run_execution_proof(*, max_rows: int = 25, timeout_s: int = 90) -> dict[str, Any]:
    paths.ensure_dirs()
    proofs: list[dict[str, Any]] = []
    for challenge in CHALLENGES:
        probe = PROBES[challenge.id]
        result = directdb.query(probe["sql"], max_rows=max_rows, timeout_s=timeout_s)
        missing = list(probe.get("missing", []))
        proofs.append(
            {
                "challenge_id": challenge.id,
                "slug": challenge.slug,
                "name": challenge.name,
                "probe": probe["name"],
                "proof_level": probe["proof_level"] if result.get("ok") else "execution-failed",
                "status": proof_status(challenge, result, missing),
                "missing": missing,
                "tables_joined": {
                    "count": len(result.get("tables", [])),
                    "tables": result.get("tables", []),
                },
                "result": result,
            }
        )

    out = {
        "generated_at": now_iso(),
        "source": "direct-postgres-readonly",
        "count": len(proofs),
        "proofs": proofs,
    }
    write_json(paths.findings_dir() / "execution-proof.json", out)
    ledger.event(
        "execution_proof_completed",
        {
            "count": len(proofs),
            "ok": sum(1 for proof in proofs if proof["result"].get("ok")),
            "failed": sum(1 for proof in proofs if not proof["result"].get("ok")),
        },
    )
    return out
