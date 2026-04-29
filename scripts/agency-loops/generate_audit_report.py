#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import html
import re
from pathlib import Path


KNOWN_BAD = [
    "fed.vw_agreement_current",
    "fed.vw_agreement_originals",
    "cra.t3010",
    "cra.t3010_schedule6",
    "general.entity_source_links.source_id",
    "general.entity_source_links.source_row_id",
    "cra.loop_universe.risk_score",
    "dept_number_en",
    "ab.grants",
]

FAKE_PLACEHOLDER_PATTERNS = [
    r"\bENT-\d+",
    r"\bFG-\d+",
    r"\bJohn Doe\b",
    r"\bJane Doe\b",
    r"\b123456789\b",
    r"\b876543210\b",
    r"\bFG-112233\b",
    r"\bFG-987654\b",
]

VERIFIED: dict[str, set[str]] = {
    "fed.grants_contributions": {
        "_id",
        "recipient_operating_name",
        "research_organization_name",
        "recipient_country",
        "recipient_province",
        "recipient_city",
        "recipient_postal_code",
        "federal_riding_name_en",
        "federal_riding_name_fr",
        "federal_riding_number",
        "prog_name_en",
        "ref_number",
        "prog_name_fr",
        "prog_purpose_en",
        "prog_purpose_fr",
        "agreement_title_en",
        "agreement_title_fr",
        "agreement_value",
        "foreign_currency_type",
        "foreign_currency_value",
        "agreement_start_date",
        "agreement_end_date",
        "amendment_number",
        "coverage",
        "description_en",
        "description_fr",
        "expected_results_en",
        "expected_results_fr",
        "additional_information_en",
        "additional_information_fr",
        "naics_identifier",
        "owner_org",
        "owner_org_title",
        "amendment_date",
        "is_amendment",
        "agreement_type",
        "agreement_number",
        "recipient_type",
        "recipient_business_number",
        "recipient_legal_name",
    },
    "ab.ab_grants": {
        "id",
        "fiscal_year",
        "display_fiscal_year",
        "lottery_fund",
        "version",
        "created_at",
        "updated_at",
        "ministry",
        "business_unit_name",
        "recipient",
        "program",
        "amount",
        "lottery",
        "payment_date",
    },
    "ab.ab_contracts": {"id", "display_fiscal_year", "recipient", "amount", "ministry"},
    "ab.ab_sole_source": {
        "id",
        "vendor_street",
        "vendor_street_2",
        "vendor_city",
        "vendor_province",
        "vendor_postal_code",
        "vendor_country",
        "start_date",
        "end_date",
        "amount",
        "contract_number",
        "ministry",
        "contract_services",
        "permitted_situations",
        "display_fiscal_year",
        "special",
        "department_street",
        "department_street_2",
        "department_city",
        "department_province",
        "department_postal_code",
        "department_country",
        "vendor",
    },
    "ab.ab_non_profit": {"id", "type", "legal_name", "status", "registration_date", "city", "postal_code"},
    "ab.vw_non_profit_decoded": {
        "id",
        "type",
        "legal_name",
        "status",
        "registration_date",
        "city",
        "postal_code",
        "status_description",
    },
    "cra.cra_identification": {
        "bn",
        "city",
        "province",
        "postal_code",
        "country",
        "registration_date",
        "language",
        "contact_phone",
        "contact_email",
        "fiscal_year",
        "category",
        "sub_category",
        "designation",
        "legal_name",
        "account_name",
        "address_line_1",
        "address_line_2",
    },
    "cra.cra_financial_details": {
        "bn",
        "fpe",
        "form_id",
        "field_4540",
        "field_4550",
        "field_4560",
        "field_4700",
    },
    "cra.govt_funding_by_charity": {
        "bn",
        "total_govt",
        "revenue",
        "govt_share_of_rev",
        "fiscal_year",
        "legal_name",
        "designation",
        "category",
        "federal",
        "provincial",
        "municipal",
        "combined_sectiond",
    },
    "cra.overhead_by_charity": {
        "bn",
        "fundraising",
        "programs",
        "strict_overhead",
        "broad_overhead",
        "strict_overhead_pct",
        "broad_overhead_pct",
        "outlier_flag",
        "fiscal_year",
        "legal_name",
        "designation",
        "category",
        "revenue",
        "total_expenditures",
        "compensation",
        "administration",
    },
    "cra.cra_compensation": {
        "bn",
        "fpe",
        "form_id",
        "field_300",
        "field_305",
        "field_310",
        "field_315",
        "field_320",
        "field_325",
        "field_330",
        "field_335",
        "field_340",
        "field_345",
        "field_370",
        "field_380",
        "field_390",
    },
    "cra.cra_qualified_donees": {
        "bn",
        "total_gifts",
        "gifts_in_kind",
        "number_of_donees",
        "political_activity_gift",
        "political_activity_amount",
        "fpe",
        "form_id",
        "sequence_number",
        "donee_bn",
        "donee_name",
        "associated",
        "city",
        "province",
    },
    "cra.loop_universe": {
        "bn",
        "max_bottleneck",
        "total_circular_amt",
        "score",
        "scored_at",
        "legal_name",
        "total_loops",
        "loops_2hop",
        "loops_3hop",
        "loops_4hop",
        "loops_5hop",
        "loops_6hop",
        "loops_7plus",
    },
    "cra.cra_directors": {
        "bn",
        "start_date",
        "end_date",
        "fpe",
        "form_id",
        "sequence_number",
        "last_name",
        "first_name",
        "initials",
        "position",
        "at_arms_length",
    },
    "cra.identified_hubs": {
        "bn",
        "legal_name",
        "scc_id",
        "in_degree",
        "out_degree",
        "total_degree",
        "total_inflow",
        "total_outflow",
        "hub_type",
    },
    "cra.johnson_cycles": {"id", "hops", "path_bns", "path_display", "bottleneck_amt", "total_flow", "min_year", "max_year"},
    "cra.loop_edges": {"src", "dst", "total_amt", "edge_count", "min_year", "max_year", "years"},
    "cra.loop_financials": {
        "loop_id",
        "hops",
        "same_year",
        "min_year",
        "max_year",
        "bottleneck_window",
        "total_flow_window",
        "bottleneck_allyears",
        "total_flow_allyears",
    },
    "cra.loop_participants": {"bn", "loop_id", "position_in_loop", "sends_to", "receives_from"},
    "cra.matrix_census": {
        "bn",
        "max_walk_length",
        "total_walk_count",
        "in_johnson_cycle",
        "in_selfjoin_cycle",
        "scc_id",
        "scc_size",
        "legal_name",
        "walks_2",
        "walks_3",
        "walks_4",
        "walks_5",
        "walks_6",
        "walks_7",
        "walks_8",
    },
    "cra.partitioned_cycles": {
        "id",
        "source_scc_id",
        "source_scc_size",
        "hops",
        "path_bns",
        "path_display",
        "bottleneck_amt",
        "total_flow",
        "min_year",
        "max_year",
        "tier",
    },
    "cra.scc_components": {"bn", "scc_id", "scc_root", "scc_size", "legal_name"},
    "cra.scc_summary": {
        "scc_id",
        "scc_root",
        "node_count",
        "edge_count",
        "total_internal_flow",
        "cycle_count_from_loops",
        "cycle_count_from_johnson",
        "top_charity_names",
    },
    "general.entity_golden_records": {
        "id",
        "source_link_count",
        "addresses",
        "cra_profile",
        "fed_profile",
        "ab_profile",
        "related_entities",
        "merge_history",
        "llm_authored",
        "confidence",
        "status",
        "canonical_name",
        "created_at",
        "updated_at",
        "norm_name",
        "entity_type",
        "bn_root",
        "bn_variants",
        "aliases",
        "dataset_sources",
        "source_summary",
    },
    "general.entity_source_links": {
        "id",
        "metadata",
        "created_at",
        "updated_at",
        "entity_id",
        "source_schema",
        "source_table",
        "source_pk",
        "source_name",
        "match_confidence",
        "match_method",
        "link_status",
    },
    "general.vw_entity_funding": {
        "entity_id",
        "canonical_name",
        "bn_root",
        "entity_type",
        "dataset_sources",
        "source_count",
        "confidence",
        "status",
        "cra_total_revenue",
        "cra_total_expenditures",
        "cra_gifts_to_donees",
        "cra_program_spending",
        "cra_filing_count",
        "cra_earliest_year",
        "cra_latest_year",
        "fed_total_grants",
        "fed_grant_count",
        "fed_earliest_grant",
        "fed_latest_grant",
        "ab_total_grants",
        "ab_grant_payment_count",
        "ab_total_contracts",
        "ab_contract_count",
        "ab_total_sole_source",
        "ab_sole_source_count",
        "total_all_funding",
    },
}


REF_RE = re.compile(r"\b(cra|fed|ab|general)\.([A-Za-z_][A-Za-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*))?")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def first_match(pattern: str, text: str) -> str:
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip() if match.groups() else match.group(0).strip()


def audit_refs(text: str) -> tuple[list[str], list[str]]:
    verified = []
    suspect = []
    for schema, table, col in REF_RE.findall(text):
        full_table = f"{schema}.{table}"
        ref = f"{full_table}.{col}" if col else full_table
        if full_table not in VERIFIED:
            suspect.append(ref)
            continue
        if col and col not in VERIFIED[full_table]:
            suspect.append(ref)
            continue
        verified.append(ref)
    return sorted(set(verified)), sorted(set(suspect))


def row_class(suspect_count: int, bad_count: int, placeholder_count: int) -> str:
    if bad_count or placeholder_count:
        return "bad"
    if suspect_count:
        return "warn"
    return "ok"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    loops = sorted([p for p in args.input.iterdir() if p.is_dir() and re.match(r"\d\d-", p.name)])
    rows = []
    detail_sections = []

    for loop in loops:
        brief = loop / "research-brief.md"
        log = loop / "correction.log"
        text = brief.read_text(errors="replace") if brief.exists() else ""
        log_text = log.read_text(errors="replace") if log.exists() else ""
        words = len(re.findall(r"\S+", text))
        digest = sha256(brief) if brief.exists() else ""
        status_line = first_match(r"Current executable status:\s*([^\n]+)", text) or "missing"
        presentation = first_match(r"Presentation sentence:\s*([^\n]+)", text) or "missing"
        correction_end = ""
        for line in log_text.splitlines():
            if "=== correction end" in line:
                correction_end = line
        bad = [bad for bad in KNOWN_BAD if bad in text]
        placeholders = []
        for pattern in FAKE_PLACEHOLDER_PATTERNS:
            if re.search(pattern, text):
                placeholders.append(pattern)
        verified_refs, suspect_refs = audit_refs(text)
        sql_blocks = len(re.findall(r"```sql", text, re.IGNORECASE))
        gaps = len(re.findall(r"\[GAP|MISSING|missing", text, re.IGNORECASE))
        klass = row_class(len(suspect_refs), len(bad), len(placeholders))
        rows.append(
            {
                "loop": loop.name,
                "words": words,
                "status": status_line,
                "presentation": presentation,
                "correction": correction_end or "missing",
                "bad": bad,
                "placeholders": placeholders,
                "verified": verified_refs,
                "suspect": suspect_refs,
                "sql_blocks": sql_blocks,
                "gaps": gaps,
                "sha": digest,
                "class": klass,
            }
        )
        detail_sections.append(
            f"""
<section class="card {klass}">
  <h2>{html.escape(loop.name)}</h2>
  <p><strong>Status:</strong> {html.escape(status_line)}</p>
  <p><strong>Presentation sentence:</strong> {html.escape(presentation)}</p>
  <p><strong>Correction log:</strong> {html.escape(correction_end or "missing")}</p>
  <p><strong>Brief SHA-256:</strong> <code>{html.escape(digest)}</code></p>
  <div class="grid">
    <div><h3>Known Bad References</h3>{list_html(bad)}</div>
    <div><h3>Suspect Schema References</h3>{list_html(suspect_refs[:30])}</div>
    <div><h3>Verified References</h3>{list_html(verified_refs[:30])}</div>
    <div><h3>Placeholder Signals</h3>{list_html(placeholders)}</div>
  </div>
</section>
"""
        )

    ok = sum(1 for row in rows if row["class"] == "ok")
    warn = sum(1 for row in rows if row["class"] == "warn")
    bad = sum(1 for row in rows if row["class"] == "bad")
    body_rows = "\n".join(
        f"""
<tr class="{row['class']}">
  <td>{html.escape(row['loop'])}</td>
  <td>{html.escape(row['status'])}</td>
  <td>{row['words']}</td>
  <td>{row['sql_blocks']}</td>
  <td>{len(row['bad'])}</td>
  <td>{len(row['suspect'])}</td>
  <td>{len(row['placeholders'])}</td>
  <td>{row['gaps']}</td>
  <td><code>{html.escape(row['sha'][:12])}</code></td>
</tr>
"""
        for row in rows
    )

    out = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Agency Loop Audit</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f6f3ee; color: #221f1c; }}
main {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
h1 {{ font-size: 34px; margin: 0 0 8px; }}
p {{ line-height: 1.5; }}
.summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 22px 0; }}
.metric {{ background: #fff; border: 1px solid #ded7ce; padding: 16px; border-radius: 8px; }}
.metric strong {{ display: block; font-size: 28px; }}
table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #ded7ce; border-radius: 8px; overflow: hidden; }}
th, td {{ padding: 10px 9px; border-bottom: 1px solid #eee7dd; text-align: left; vertical-align: top; font-size: 14px; }}
th {{ background: #25211c; color: white; }}
tr.ok td:first-child {{ border-left: 5px solid #2e7d4f; }}
tr.warn td:first-child {{ border-left: 5px solid #b88700; }}
tr.bad td:first-child {{ border-left: 5px solid #b23b3b; }}
.card {{ background: #fff; border: 1px solid #ded7ce; border-radius: 8px; padding: 18px; margin-top: 18px; }}
.card.ok {{ border-left: 6px solid #2e7d4f; }}
.card.warn {{ border-left: 6px solid #b88700; }}
.card.bad {{ border-left: 6px solid #b23b3b; }}
.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
code {{ background: #f1ece4; padding: 2px 4px; border-radius: 4px; }}
ul {{ padding-left: 19px; }}
.note {{ background: #fff7dd; border: 1px solid #e0bf5f; padding: 12px; border-radius: 8px; }}
</style>
</head>
<body>
<main>
<h1>Agency Loop Audit</h1>
<p>This report audits the ten parallel research loops after the schema-correction pass. It checks for known hallucinated views, suspect table or column references, placeholder examples, executable status lines, SQL blocks, and correction-log completion.</p>
<p class="note">This is a lexical audit over the briefs, not a proof that every SQL block has executed. A brief is presentation-safe only when bad references are zero and the claim language matches its executable status.</p>
<div class="summary">
  <div class="metric"><span>Loops</span><strong>{len(rows)}</strong></div>
  <div class="metric"><span>Clean</span><strong>{ok}</strong></div>
  <div class="metric"><span>Needs Review</span><strong>{warn}</strong></div>
  <div class="metric"><span>Unsafe</span><strong>{bad}</strong></div>
</div>
<h2>Summary Table</h2>
<table>
  <thead><tr><th>Loop</th><th>Status</th><th>Words</th><th>SQL</th><th>Known Bad</th><th>Suspect Refs</th><th>Placeholders</th><th>Gaps</th><th>SHA</th></tr></thead>
  <tbody>{body_rows}</tbody>
</table>
<h2>Audit Trail Details</h2>
{''.join(detail_sections)}
</main>
</body>
</html>
"""
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(out)


def list_html(items: list[str]) -> str:
    if not items:
        return "<p>None.</p>"
    return "<ul>" + "".join(f"<li><code>{html.escape(item)}</code></li>" for item in items) + "</ul>"


if __name__ == "__main__":
    main()
