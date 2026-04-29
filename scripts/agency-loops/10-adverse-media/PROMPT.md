# Loop 10 — Adverse Media

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Adverse Media**.

## The Challenge (verbatim)

> Which organizations receiving public funding are the subject of serious adverse media coverage? This means regulatory enforcement actions, fraud allegations, safety incidents, criminal investigations, and sanctions. Not political controversy, not critical op-eds. The challenge is precision: build a system that distinguishes genuine red-flag reporting from noise, and match it against the funding data to identify recipients whose public record should concern a funder.

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **What "adverse media" means in this challenge**: regulatory enforcement (CSA/CIRO/OSC market actions, Competition Bureau orders), criminal investigations (RCMP, provincial police, Public Prosecution Service), safety incidents (Transport Canada incident reports, ESDC OHS rulings), sanctions (Office of the Superintendent of Financial Institutions, Bank of Canada sanctions list, Global Affairs Canada SEMA Russia/Belarus/etc. lists). Not editorial criticism.
- **Authoritative public sources**:
  - CRA Charity revocation register: https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/dsplyAdvncdSrch
  - Competition Bureau enforcement: https://competition-bureau.canada.ca/en/case-history
  - Securities regulators: CSA national database; OSC and provincial regulators publish enforcement decisions.
  - Sanctions lists: SEMA, JVCFOA, Special Economic Measures.
  - OpenCorporates Canadian slice (partial).
  - GDELT / GNEWS API for newswire (paid + signup).
  - Court decisions: CanLII has Canadian case law indexed.
- **GovAlta data**: there is no adverse-media field. This challenge requires external data ingestion + name matching against funded entities. The `general.entity_golden_records` is the join target (canonical_name + bn_root + aliases).
- **Methodology**: build a watchlist of regulator/sanctions/court mentions per entity, score by source authority + recency + adverseness category, attach to canonical entities. False-positive risk is high — same name, different entity. Identity validation requires BN match where possible; otherwise probabilistic with explicit confidence.
- **The precision burden**: "Telus Health Solutions" gets dozens of news mentions per month, most neutral. The methodology must filter on adverseness, not volume.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md`
- The OFAC / SEMA sanctions formats for inspiration.

## Reminders

- This challenge cannot be solved offline. The brief must be honest about that.
- Cite real public regulators and registries. No invented databases.
- A fully-worked example with one specific regulator action against a federal grantee is required if you can find one in public record; otherwise mark `[GAP: need public-record example]`.

Begin.
