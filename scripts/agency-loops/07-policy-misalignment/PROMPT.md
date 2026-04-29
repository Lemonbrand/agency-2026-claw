# Loop 07 — Policy Misalignment

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Policy Misalignment**.

## The Challenge (verbatim)

> Is the money going where the government says its priorities are? Pick specific, measurable policy commitments (emissions targets, housing starts, reconciliation spending, healthcare capacity) and compare them to the actual flow of funds. The challenge is not abstract. It is concrete: does the spending pattern match the stated plan, and where are the biggest gaps between rhetoric and allocation?

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **The hard part**: policy commitments live in budget speeches, throne speeches, departmental plans, mandate letters, federal budgets (DOF), provincial budgets, and party platforms. None ship as structured open data. Manual extraction or LLM-assisted extraction with citation discipline is required.
- **Authoritative sources for policy text**:
  - Federal Budget documents (https://www.budget.canada.ca/) — annual, PDF + HTML.
  - Departmental Plans + Departmental Results Reports on https://www.canada.ca/en/treasury-board-secretariat/services/planned-government-spending.html
  - Mandate letters at https://www.pm.gc.ca/en/mandate-letters
  - Throne speeches at https://www.canada.ca/en/privy-council/services/publications/speech-throne.html
  - Alberta budgets at https://www.alberta.ca/budget
- **Spending data we have**: FED + AB at row level. CRA charities receive but do not allocate.
- **Concrete worked example to anchor the brief**: pick ONE measurable commitment (suggested: federal emissions-reduction target as expressed in the Emissions Reduction Plan + Net-Zero Accountability Act, vs. fossil-fuel-related federal spending in `fed.grants_contributions` filtered by NAICS / department / program keywords). Or: federal "rural broadband" commitments (Universal Broadband Fund, $3.225B) vs. actual UBF disbursements per `prog_name_en` LIKE '%Broadband%'.
- **Reconciliation spending**: Crown-Indigenous Relations + Indigenous Services Canada appear as `owner_org_title` values; ISC was created from INAC in 2017.
- **Methodology gotcha**: spending labels move across departments and programs over time. A policy commitment from year N may map to program X in year N and program Y in year N+2 after reorganization.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md`
- The TBS Open Government data inventory.

## Reminders

- This is the hardest of the ten challenges. The brief should be honest about the natural-language alignment problem.
- Concrete worked example > abstract methodology. Pick one commitment and trace it.

Begin.
