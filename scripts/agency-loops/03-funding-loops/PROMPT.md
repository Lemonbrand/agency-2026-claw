# Loop 03 — Funding Loops

You are one of ten parallel research agents tackling Canadian government accountability challenges. Your sole challenge is **Funding Loops**.

## The Challenge (verbatim)

> Where does money flow in circles between charities, and does it matter? Using CRA T3010 data, identify circular funding patterns: reciprocal gifts, triangular cycles, and longer chains where dollars leave an organization and eventually return to it. Most loops are structurally normal (denominational hierarchies, federated charities, donation platforms). The challenge is distinguishing these from loops that exist to inflate revenue, generate tax receipts, or absorb funds into overhead without delivering charitable programs.

## Your Goal

Produce `research-brief.md` per `../STRUCTURE.md`. Jury-ready.

## Domain priors

- **CRA already did this**: the GovAlta dataset includes precomputed `cra.loop_universe` (per-BN risk score 0-30), `cra.loops` (2-6 hop cycles, 5,808 rows), `cra.loop_participants`, `cra.loop_edges`, `cra.loop_financials`, `cra.scc_components` (strongly-connected components), `cra.scc_summary`, `cra.johnson_cycles` (4,601 simple cycles), `cra.partitioned_cycles` (108), `cra.identified_hubs` (20 high-degree BNs), `cra.matrix_census`. The cross-validation between Johnson's algorithm and self-join is documented in C-12 of `KNOWN-DATA-ISSUES.md`.
- **Source data**: `cra.cra_qualified_donees` (1.66M rows) is the per-charity list of Schedule 5 gifts to other qualified donees, with `donee_bn`, `donee_name`, `total_gifts`. Quality issues: see C-3 (donee BN→name mismatches, $8.97B unjoinable), C-11 (20,192 unregistered donee BNs).
- **Distinguishing structural-normal from anomalous**: denominational hierarchies (Salvation Army, Catholic dioceses) and federated charities (United Way, Centraide) form large normal loops. Donor-advised funds (Canada Gives, Charitable Impact) are donation platforms with high inbound + outbound counts. The score in `loop_universe` already weights bottleneck size + cycle length + circular volume, but does not encode "is this denominational?". A second classifier or human review pass distinguishes them.
- **Risk amplifiers**: cycle that closes within a single fiscal period (round-tripping for receipts), tiny loops where each leg is at the gift threshold, single-director-shared cycles.

## Read first

- `../STRUCTURE.md`
- `../KNOWN-DATA-ISSUES-NOTES.md` (C-3, C-11, C-12 are directly relevant)

## Reminders

- This is the strongest precomputation in the entire dataset. The agent's value is the framing + classification + caveat layer, not rebuilding the cycle detection.
- The Globe & Mail / Canadaland precedents on charity loops should be cited if you have them confirmed; otherwise mark as `[GAP]`.

Begin.
