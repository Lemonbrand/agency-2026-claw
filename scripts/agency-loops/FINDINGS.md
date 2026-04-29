# Findings — what the constellation has produced

Curated reading of the 10 parallel research briefs. Updated each cron cycle. The briefs themselves live at `/opt/lemon-agency/<NN>/research-brief.md` on the VPS; this file is the meta-extract.

Architecture in motion:

- **GLM 5.1** generates each brief, six sections, in parallel.
- **Codex GPT-5.2** produced `VERIFIED_SCHEMA.md` + `CORRECTION_PASS.md` once it caught hallucinated table references; second-pass tmux sessions named `agency-correct-*` re-iterate every brief with the verification layer in the read set.
- **Claude (this orchestrator)** notes findings here every cron cycle.

## Cycle 2 — 09:38 ET / 13:38 UTC

### Per-loop state

| # | Challenge | Brief KB | Status | Headline so far |
|---|---|---:|---|---|
| 01 | Zombie Recipients | 15.8 | original-pass complete | Splits "stopped filing" (administrative) from "legally dissolved" (FOI-only). Explicitly names Corporations Canada + provincial registries as the missing-data sources. |
| 02 | Ghost Capacity | 5.5 | thin (was relaunched, mid-flight) | Pre-correction-pass; first-pass struggled. Codex's correction adds explicit caveat: "do not call hospitals, school boards, or public health authorities ghost-capacity leads without exclusion." |
| 03 | Funding Loops | 17.0 | **COMPLETE** + correction pending | Composite risk score `0.4·Volume + 0.3·Velocity + 0.2·Overhead + 0.1·Director_Overlap`. Disconfirming check handles donor-advised funds. False-positive cohort = 1-hop neighborhood of `cra.identified_hubs` (20 BNs). |
| 04 | Sole Source / Amendment Creep | 6.9 | thin, mid-flight | First pass was thin. Second pass should pick up the threshold-just-below pattern referencing TBS Contracting Policy values. |
| 05 | Vendor Concentration | 16.8 | **COMPLETE** + correction pending | HHI > 2500 (US DOJ) flag. Temporal drift analysis distinguishes "drifted into incumbency" from "natural monopoly". Statutory monopoly cross-reference. Explicit F-10 guard ("agreement_number never a join key"). |
| 06 | Related Parties | 16.4 | mid-flight, near max iter | Director name match via `cra.cra_directors` with C-6 NULL caveats. Honest about the corporate-registry gap (federally incorporated only in Corporations Canada; provincial coverage is ad-hoc). |
| 07 | Policy Misalignment | 13.9 | mid-flight | Worked example anchors on federal emissions-reduction commitment vs fossil-fuel-related federal spending. Honest about the natural-language alignment problem. |
| 08 | Duplicative Funding | 13.0 | mid-flight | Leans on `general.entity_golden_records` directly. Embedding similarity on `prog_name_en` × AB `program` for same-purpose validation. The funding-gaps inverse correctly punts to Loop 07. |
| 09 | Contract Intelligence | 14.7 | **COMPLETE** + correction pending | Log-linear decomposition `ΔTotal ≈ ΔVolume·UnitCost(t-1) + Volume(t-1)·ΔUnitCost`. PPI Table 18-10-0030-01 deflation. Pre-COVID vs post-COVID cohort split. |
| 10 | Adverse Media | 18.2 | mid-flight, largest brief | Distinguishes regulator enforcement (Competition Bureau, CSA, OSC, OFSI) from editorial criticism. Honest that the dataset cannot solve this offline. Names CanLII as the case-law source. |

### Cross-loop patterns

- **`general.entity_golden_records` is the universal join key.** Loops 01, 03, 05, 06, 08, 09, 10 all explicitly route through it. The 851K canonical entities are the layer that makes cross-jurisdictional analysis tractable — and Codex's verification confirmed the schema is real.
- **Hallucination caught and corrected in flight.** Three completed briefs (03, 05, 09) all referenced `fed.vw_agreement_current` as if it were a live view. Codex's VERIFIED_SCHEMA called it out, supplied the F-3-safe CTE workaround, and the second-pass tmux sessions are re-running with the correction in the read set. The hallucination → correction round-trip happened in <40 minutes.
- **Honest gap declaration is consistent across loops.** Every brief that touches missing data (legal dissolution, corporate-registry principals, intra-year transaction timestamps, adverse-media wire) names the gap with specificity rather than papering over it. That posture is the demo's credibility layer.

### Most impressive single passage

Loop 03's disconfirming check on funding loops:

> **Disconfirming Check:** What would prove this finding wrong? If the identified "anomalous" loops are overwhelmingly composed of donor-advised funds (DAFs) or registered national charities acting as intermediaries (e.g., Canada Gives), the finding of "inflation" is false. DAFs legally must disburse, creating high-velocity, high-volume loops that are structurally normal. We must verify that our `cra.identified_hubs` and `matrix_census` degree filters successfully excluded DAFs.

That is the kind of self-falsification a deputy minister wants to see before any finding leaves the building.

### One honest critique

GLM 5.1's first pass was confidently wrong about specific objects in the schema (the `fed.vw_agreement_current` view, `cra.t3010` as a single table, `cra.loop_universe.risk_score` instead of `score`). The methodology around the wrong objects was sound; the references were not. Without Codex's verification layer the briefs would have read well to a non-DBA and then crashed on first-run. The two-brain architecture is doing real work, not theatre. Sovereignty conclusion: the verification layer matters, and a Canadian-hosted equivalent of the verifying brain is part of the policy ask, not a nice-to-have.
