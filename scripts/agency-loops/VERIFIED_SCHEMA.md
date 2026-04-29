# Verified GovAlta Schema Contract

Use this file as the source of truth for GovAlta database references. If a table or column is not listed here, do not cite it as available. Mark it as `[GAP]` or replace it with a listed equivalent.

## Global Rule

Before a research brief says `AVAILABLE`, the referenced `schema.table.column` must exist here.

Do not cite these as available. They were assumed in earlier drafts but are not present in the live schema:

- `fed.vw_agreement_current`
- `fed.vw_agreement_originals`
- `cra.t3010`
- `cra.t3010_schedule6`
- `general.entity_source_links.source_id`
- `general.entity_source_links.source_row_id`
- `cra.loop_universe.risk_score`
- `dept_number_en`

## Federal Grants

### `fed.grants_contributions`

Columns:

- `_id`
- `recipient_operating_name`
- `research_organization_name`
- `recipient_country`
- `recipient_province`
- `recipient_city`
- `recipient_postal_code`
- `federal_riding_name_en`
- `federal_riding_name_fr`
- `federal_riding_number`
- `prog_name_en`
- `ref_number`
- `prog_name_fr`
- `prog_purpose_en`
- `prog_purpose_fr`
- `agreement_title_en`
- `agreement_title_fr`
- `agreement_value`
- `foreign_currency_type`
- `foreign_currency_value`
- `agreement_start_date`
- `agreement_end_date`
- `amendment_number`
- `coverage`
- `description_en`
- `description_fr`
- `expected_results_en`
- `expected_results_fr`
- `additional_information_en`
- `additional_information_fr`
- `naics_identifier`
- `owner_org`
- `owner_org_title`
- `amendment_date`
- `is_amendment`
- `agreement_type`
- `agreement_number`
- `recipient_type`
- `recipient_business_number`
- `recipient_legal_name`

Current/latest agreement values must be computed with a CTE, not a non-existent view:

```sql
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
      PARTITION BY ref_number, COALESCE(recipient_business_number, recipient_legal_name)
      ORDER BY COALESCE(amendment_date, agreement_start_date) DESC NULLS LAST,
               CAST(amendment_number AS VARCHAR) DESC NULLS LAST
    ) AS rn
  FROM fed.grants_contributions
  WHERE ref_number IS NOT NULL
    AND agreement_value IS NOT NULL
    AND agreement_value > 0
)
SELECT * FROM ranked WHERE rn = 1;
```

Original agreement values must be computed from `is_amendment = false`:

```sql
SELECT
  ref_number,
  COALESCE(recipient_business_number, recipient_legal_name) AS recipient_key,
  recipient_legal_name,
  owner_org_title,
  agreement_value AS original_value,
  agreement_start_date
FROM fed.grants_contributions
WHERE is_amendment = false
  AND agreement_value IS NOT NULL
  AND agreement_value > 0
  AND ref_number IS NOT NULL;
```

## Alberta

### `ab.ab_grants`

Columns:

- `id`
- `fiscal_year`
- `display_fiscal_year`
- `lottery_fund`
- `version`
- `created_at`
- `updated_at`
- `ministry`
- `business_unit_name`
- `recipient`
- `program`
- `amount`
- `lottery`
- `payment_date`

### `ab.ab_contracts`

Columns:

- `id`
- `display_fiscal_year`
- `recipient`
- `amount`
- `ministry`

### `ab.ab_sole_source`

Columns:

- `id`
- `vendor_street`
- `vendor_street_2`
- `vendor_city`
- `vendor_province`
- `vendor_postal_code`
- `vendor_country`
- `start_date`
- `end_date`
- `amount`
- `contract_number`
- `ministry`
- `contract_services`
- `permitted_situations`
- `display_fiscal_year`
- `special`
- `department_street`
- `department_street_2`
- `department_city`
- `department_province`
- `department_postal_code`
- `department_country`
- `vendor`

### `ab.ab_non_profit`

Columns:

- `id`
- `type`
- `legal_name`
- `status`
- `registration_date`
- `city`
- `postal_code`

### `ab.vw_non_profit_decoded`

Adds:

- `status_description`

There is registration/status information, but no reliable dissolution date in the inspected schema.

## CRA

### `cra.cra_identification`

Columns include:

- `bn`
- `city`
- `province`
- `postal_code`
- `country`
- `registration_date`
- `language`
- `contact_phone`
- `contact_email`
- `fiscal_year`
- `category`
- `sub_category`
- `designation`
- `legal_name`
- `account_name`
- `address_line_1`
- `address_line_2`

Use this for legal name, BN, location, registration date, and filing-year presence. It does not provide revocation date or dissolution date.

### `cra.cra_financial_details`

Relevant columns:

- `bn`
- `fpe`
- `form_id`
- `field_4540` federal government revenue
- `field_4550` provincial or territorial government revenue
- `field_4560` municipal or regional government revenue
- `field_4700` total revenue
- `field_5000` through expenditure lines

### `cra.govt_funding_by_charity`

Use this instead of reconstructing government share when possible.

Columns:

- `bn`
- `total_govt`
- `revenue`
- `govt_share_of_rev`
- `fiscal_year`
- `legal_name`
- `designation`
- `category`
- `federal`
- `provincial`
- `municipal`
- `combined_sectiond`

### `cra.overhead_by_charity`

Columns:

- `bn`
- `fundraising`
- `programs`
- `strict_overhead`
- `broad_overhead`
- `strict_overhead_pct`
- `broad_overhead_pct`
- `outlier_flag`
- `fiscal_year`
- `legal_name`
- `designation`
- `category`
- `revenue`
- `total_expenditures`
- `compensation`
- `administration`

### `cra.cra_compensation`

Columns:

- `bn`
- `fpe`
- `form_id`
- `field_300`
- `field_305`
- `field_310`
- `field_315`
- `field_320`
- `field_325`
- `field_330`
- `field_335`
- `field_340`
- `field_345`
- `field_370`
- `field_380`
- `field_390`

Use these as compensation-band indicators only if the brief explains the T3010 line meaning. Do not call them direct employee counts unless the line definition is cited.

### `cra.cra_qualified_donees`

Columns:

- `bn`
- `total_gifts`
- `gifts_in_kind`
- `number_of_donees`
- `political_activity_gift`
- `political_activity_amount`
- `fpe`
- `form_id`
- `sequence_number`
- `donee_bn`
- `donee_name`
- `associated`
- `city`
- `province`

### `cra.loop_universe`

Columns:

- `bn`
- `max_bottleneck`
- `total_circular_amt`
- `score`
- `scored_at`
- `legal_name`
- `total_loops`
- `loops_2hop`
- `loops_3hop`
- `loops_4hop`
- `loops_5hop`
- `loops_6hop`
- `loops_7plus`

Use `score`, not `risk_score`.

Other available loop tables include:

- `cra.johnson_cycles`
- `cra.partitioned_cycles`
- `cra.loop_edges`
- `cra.loop_edge_year_flows`
- `cra.loop_participants`
- `cra.loop_financials`
- `cra.scc_components`
- `cra.scc_summary`
- `cra.matrix_census`
- `cra.identified_hubs`

## General Entity Resolution

### `general.entity_golden_records`

Columns:

- `id`
- `source_link_count`
- `addresses`
- `cra_profile`
- `fed_profile`
- `ab_profile`
- `related_entities`
- `merge_history`
- `llm_authored`
- `confidence`
- `status`
- `canonical_name`
- `created_at`
- `updated_at`
- `norm_name`
- `entity_type`
- `bn_root`
- `bn_variants`
- `aliases`
- `dataset_sources`
- `source_summary`

### `general.entity_source_links`

Columns:

- `id`
- `metadata`
- `created_at`
- `updated_at`
- `entity_id`
- `source_schema`
- `source_table`
- `source_pk`
- `source_name`
- `match_confidence`
- `match_method`
- `link_status`

Use `source_pk`, not `source_id` or `source_row_id`.

### `general.vw_entity_funding`

Columns:

- `entity_id`
- `canonical_name`
- `bn_root`
- `entity_type`
- `dataset_sources`
- `source_count`
- `confidence`
- `status`
- `cra_total_revenue`
- `cra_total_expenditures`
- `cra_gifts_to_donees`
- `cra_program_spending`
- `cra_filing_count`
- `cra_earliest_year`
- `cra_latest_year`
- `fed_total_grants`
- `fed_grant_count`
- `fed_earliest_grant`
- `fed_latest_grant`
- `ab_total_grants`
- `ab_grant_payment_count`
- `ab_total_contracts`
- `ab_contract_count`
- `ab_total_sole_source`
- `ab_sole_source_count`
- `total_all_funding`

## Quick Feasibility Counts Already Observed

These are not final findings. They are scouting counters from live schema inspection.

- Ghost-capacity strict candidate count: 353 using high government share, low program-spend ratio, low compensation ratio, and small compensation-band count.
- Zombie stopped-filing/high-gov-share candidate count: 806 using `cra.govt_funding_by_charity` latest filing year and high government share. This is only a stopped-filing signal, not legal dissolution.
- Federal concentration: 3,761 department-program groups over $1M where one recipient has at least 70 percent share.
- Federal grants date coverage: 2019 through 2027 in `fed.grants_contributions.agreement_start_date`.
- Alberta sole-source date coverage: 1975 through 2025 in `ab.ab_sole_source.start_date`, with the main event-era values concentrated 2014 through 2026 by `display_fiscal_year`.
