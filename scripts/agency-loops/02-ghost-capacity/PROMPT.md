# Loop 02 — Ghost Capacity

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Ghost Capacity**.

## The Challenge (verbatim)

> Which funded organizations show no evidence of actually being able to deliver what they were funded to do? Look for entities with no employees, no physical presence, and no revenue beyond government transfers, where expenditures flow almost entirely to compensation for a small number of individuals or to further transfers to other entities. These are not zombies. Zombies die. Ghost-capacity entities persist indefinitely. They just never do anything.

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready: concrete, sourced, replayable.

## Domain priors

- **T3010 capacity signals (CRA `cra.cra_financial_details`)**:
  - `field_4540` + `field_4550` + `field_4560` = total government revenue
  - `field_4700` = total revenue (denominator for gov-share)
  - `field_4880` = total compensation (Schedule 6 / Schedule 3)
  - `field_4950` = expenditures on charitable activities
  - `field_5100` = total expenditures
  - `field_5031` / `field_5032` (post-2024 form) = transfers to qualified donees
  - `cra.cra_compensation` per-position breakdown (top-10 paid + part-time/full-time counts) — this is your "no employees" proxy
- **No physical presence**: `cra.cra_identification.address_line_1` is mandatory; absence is rare. Better proxies: `field_4101`/`field_4102` (real-estate assets) zero, plus residential-shaped address (PO box, apartment unit, registered-agent address).
- **Persistence**: filed in 5/5 years 2020-2024 with the same low-activity profile.
- **CRA already publishes** `cra.govt_funding_by_charity` and `cra.overhead_by_charity` precomputed.
- The signal you want: high `gov_share` AND tiny employee count AND high `compensation/program_spend` ratio AND low real-estate AND multi-year persistence.
- Disconfirming check: pure grant-making foundations (designation `F`) by definition look like ghost capacity. They are not. Filter `cra.cra_identification.designation` codes.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md`

## Reminders

- The T3010 form-line citations live at https://www.canada.ca/en/revenue-agency/services/forms-publications/forms/t3010.html.
- The 86 financial fields are mapped in CRA's Open Data Dictionary v2.0.
- This challenge is about persistence + thin capacity — not just a snapshot. Methodology must be multi-year.

Begin with the skeleton. Iterate to depth.
