# Loop 01 — Zombie Recipients

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Zombie Recipients**.

## The Challenge (verbatim from the hackathon brief)

> Which companies and nonprofits received large amounts of public funding and then ceased operations shortly after? Identify entities that went bankrupt, dissolved, or stopped filing within 12 months of receiving funding. Flag entities where public funding makes up more than 70-80% of total revenue, meaning they likely could not survive without it. The question is simple: did the public get anything for its money, or did it fund a disappearing act?

## Your Goal

Produce `research-brief.md` per the six-section structure in `../STRUCTURE.md`. Every section must be jury-ready: concrete, sourced, replayable.

## Domain priors for this challenge

- **GovAlta dataset coverage**: CRA `cra.cra_identification` carries `bn`, `legal_name`, `fiscal_year` (latest filing year), `registration_date`, but does NOT carry a `revocation_date` or `status_code` directly. CRA publishes a separate "List of charities" with effective dates and revocation reasons. FED `fed.grants_contributions` has `agreement_start_date`, `agreement_end_date`, `agreement_value` (cumulative — apply F-3 mitigation). AB `ab.ab_grants`, `ab.ab_contracts`, `ab.ab_sole_source` have payment dates per row. `general.entity_golden_records` joins all three.
- **The 70-80% threshold**: T3010 fields `field_4540` (revenue from federal government), `field_4550` (revenue from provincial/territorial), `field_4560` (revenue from municipal/regional). Total revenue at `field_4700`. Compute `gov_share = (4540+4550+4560) / 4700`.
- **The "stopped filing" signal**: a charity that filed in year Y and has no T3010 row in year Y+1, Y+2 is a candidate zombie. The hackathon dataset only spans 2020-2024; recent zombies (post-2024) cannot be detected from this snapshot alone.

## Read first

- `../STRUCTURE.md` (the deliverable shape)
- `../KNOWN-DATA-ISSUES-NOTES.md` (data quality footguns to encode into the methodology)

## Reminders

- No invented URLs. If you cite the CRA Charity Listings, cite the real one.
- Distinguish "stopped filing" (administrative) from "actually dissolved" (legal). Different sources, different confidence.
- The disconfirming check matters: the entity may have merged, rebranded, or been wound down on purpose. Name how the methodology handles each.

Begin by writing or refining `research-brief.md`. The first iteration should produce a strong skeleton with all six sections present even if thin. Subsequent iterations expand the weakest section.
