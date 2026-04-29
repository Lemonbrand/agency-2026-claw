# Loop 06 — Related Parties and Governance Networks

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Related Parties and Governance Networks**.

## The Challenge (verbatim)

> Who controls the entities that receive public money, and do they also control each other? Cross-reference directors from CRA T3010 filings with corporate registries and contract data. Identify individuals who sit on multiple boards of organizations that fund each other, principals of companies receiving contracts who are also directors of charities receiving grants, and former public servants connected to entities funded by their former departments.

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **Director data we have**: `cra.cra_directors` (~2.87M rows): bn, last_name, first_name, start_date, end_date, position, at_arms_length. Quality: C-6 — first_name 0.11% NULL (rare), at_arms_length 4.96% NULL, start_date 10% NULL, end_date 75.8% NULL (expected for currently serving directors). first_name + last_name is the only join key — name-only matching is brittle, identity validation is required before any governance claim.
- **Corporate registry**: federally incorporated companies are in the Corporations Canada online database (https://www.ic.gc.ca/app/scr/cc). Provincial registries vary: Alberta has Corporate Registry; Ontario has ServiceOntario. None ship as bulk open data. The OpenCorporates Canada slice is partial. **Major gap**.
- **Contract data**: `fed.grants_contributions.recipient_legal_name` and `ab.ab_*.recipient` carry the company name only, not principals. Cross-referencing director names against vendor principals requires registry data.
- **Former public servants**: there is no clean public dataset linking person → department → years served. Lobby Registry (https://lobbycanada.gc.ca/) names registrants; "designated public office holders" lists exist via the Office of the Conflict of Interest and Ethics Commissioner. Both are partial.
- **`general.entity_golden_records`**: the entity-resolution layer canonicalizes organization names but NOT person names. Person disambiguation is open work in this dataset.
- **The honest framing**: we cannot fully solve this challenge from the GovAlta data alone. Charity board overlaps yes; corporate-registry-to-charity-director cross-link no. The methodology must be explicit about that boundary.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md` (C-6 is directly relevant)
- Lobbying Registry docs at https://lobbycanada.gc.ca/

## Reminders

- Identity validation = the bottleneck. Every name-only finding must carry that caveat.
- The Globe & Mail "Charity Watch" series is a precedent worth citing if confirmed.

Begin.
