# Loop 09 — Contract Intelligence

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Contract Intelligence**.

## The Challenge (verbatim)

> What is Canada actually buying, and is it paying more over time? Identify which categories of procurement have seen the fastest cost growth, and decompose whether that growth comes from volume, unit cost, or vendor concentration. Surface the contracts and categories where taxpayers are getting less for more.

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **Decomposition formula**: total_spend(t) = volume(t) × unit_cost(t). Year-over-year change ΔTotalSpend ≈ ΔVolume × unitCost(t-1) + volume(t-1) × ΔUnitCost + interaction. Categories with rising unit cost AND rising vendor concentration are the priority list (procurement leverage problem). Rising volume alone is not necessarily a story; it can reflect program scale-up.
- **Category taxonomy**: federal contracts have NAICS-like classification but FED.grants_contributions uses department + program rather than NAICS. The Open Contracting Data Standard (OCDS) Canadian feed at https://search.open.canada.ca/contracts/ is more granular. Alberta uses ministry × program but no commodity classification.
- **Inflation deflation**: CPI alone is not the right deflator for procurement; better is an industry-specific PPI (Statistics Canada Producer Price Indexes by NAICS, table 18-10-0030). Without deflation, "cost growth" partially reflects inflation, not procurement leverage.
- **GovAlta data slice**: `fed.grants_contributions` has `prog_name_en`, `agreement_value` (use F-3-safe view), `agreement_start_date` for time series. AB `ab_grants` has `display_fiscal_year`, `program`, `amount`. AB `ab_contracts` has only fiscal_year + ministry + recipient + amount; no category.
- **Time horizon**: dataset spans 2006-2025 federal, 2014-2026 Alberta. Growth analysis needs at least 3-5 years to be meaningful; the post-COVID structural shift means pre-2020 vs. post-2020 trends should be analyzed separately.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md` (F-3 is critical for accurate totals over time)
- StatsCan PPI tables on https://www150.statcan.gc.ca/

## Reminders

- The decomposition (volume vs unit-cost vs concentration) is what distinguishes this from a basic "spend grew" finding.
- IT services + professional services are likely the dominant growth categories; verify against data, do not assume.
- A worked example with one specific high-growth program is required.

Begin.
