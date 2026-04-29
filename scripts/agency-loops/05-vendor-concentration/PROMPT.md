# Loop 05 — Vendor Concentration

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Vendor Concentration**.

## The Challenge (verbatim)

> In any given category of government spending, how many vendors are actually competing? Identify areas where a single supplier or a small group of suppliers receives a disproportionate share of contracts. Measure concentration by category, department, and region. Where has incumbency replaced competition? Where has government become dependent on a vendor it can no longer walk away from?

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **Standard concentration metric**: Herfindahl-Hirschman Index (HHI). HHI = sum of squared vendor shares (as percentages, scale 0-10000). HHI < 1500 = competitive, 1500-2500 = moderately concentrated, > 2500 = highly concentrated (US DOJ thresholds, also referenced in Canadian Competition Bureau merger guidelines). Top-1, top-3, top-5 share are simpler but lossier measures.
- **FED slice**: `fed.grants_contributions` rolled up to (department=`owner_org_title`, program=`prog_name_en`, vendor=`recipient_business_number`/`recipient_legal_name`) over time. Use the F-3-safe view (latest amendment per `ref_number`+recipient).
- **AB slice**: `ab.ab_contracts` (ministry × recipient × amount) and `ab.ab_sole_source` (ministry × vendor × amount). Sole-source is the more interesting concentration cohort.
- **Region**: federal grants carry `recipient_province`. AB is single-province by definition. CRA charities have province + city.
- **The challenge nuance**: a sole vendor in a niche category may be a natural monopoly (e.g., a single defence prime, a regulated utility). The methodology must distinguish "deliberate sole-source from natural monopoly" from "drifted into incumbency."
- **Cross-validation**: federal Open Government already publishes a "Federal contracts" dataset with NAICS codes; FED.grants_contributions does NOT carry NAICS in usable form (the column exists but is sparse). Reference the CFP+ open-contracting data if needed.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md` (F-3, F-6, F-7, F-10 are critical for accurate vendor totals)
- TBS Open Government contracts page on https://open.canada.ca/data/en/dataset

## Reminders

- HHI ≠ a finding. HHI = a screening metric. Each high-HHI cohort needs a follow-on investigation (procurement method, framework status, statutory monopoly status).

Begin.
