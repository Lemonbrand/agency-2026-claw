# Loop 04 — Sole Source and Amendment Creep

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Sole Source and Amendment Creep**.

## The Challenge (verbatim)

> Which contracts started small and competitive but grew large through sole-source amendments? Identify patterns where the amended value of a contract dwarfs the original bid, where contracts are split just below competitive thresholds, or where the same vendor wins the initial competition and then receives ongoing sole-source work. The goal is to surface procurement relationships that may have quietly outgrown their original justification.

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **FED `fed.grants_contributions`** has `ref_number`, `amendment_number`, `is_amendment`, `agreement_value`, `amendment_date`. **Critical: F-3.** `agreement_value` is cumulative, not a delta. Naive SUM inflates the federal total by ~$388B (~73%). The mitigation is the latest-amendment-per-(ref_number, recipient_key) pattern. F-1 (41,046 colliding `ref_number`s across distinct recipients) requires (`ref_number`, `recipient_business_number`) as the partition key.
- **AB `ab.ab_contracts`** is thin: `id, display_fiscal_year, recipient, amount, ministry`. No original-vs-current distinction available. `ab.ab_sole_source` carries `vendor, amount, ministry, contract_services, permitted_situations, special, start_date, end_date`. The `permitted_situations` column uses opaque letter codes a–l + z (see A-4 in `KNOWN-DATA-ISSUES.md`); positional inference exists but is not Alberta-confirmed.
- **Threshold-just-below patterns**: federal procurement competitive thresholds are published in the Treasury Board Contracting Policy. Notable values: $25,000 for goods (low-value), $40,000 for services (low-value), trade-agreement thresholds for CETA / CFTA / CPTPP that change over time. A contract clustering just below a threshold is a candidate.
- **Same-vendor-then-sole-source pattern**: requires temporal sequence per (vendor, department) showing competitive award followed by N sole-source amendments or follow-on contracts.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md` (F-1 through F-11, A-3, A-4 all relevant)
- The Treasury Board procurement-thresholds page on https://www.tbs-sct.canada.ca/

## Reminders

- "Amendment creep" and "sole-source dominance" are two patterns inside one challenge. Cover both, separately, with one fully-worked example per pattern.

Begin.
