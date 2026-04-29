# LemonClaw Instructions

This repo is the LemonClaw local-first accountability story engine. Built for the Agency 2026 Ottawa hackathon, designed to outlive it.

Core rule: optimize for auditable truth, not demo magic. Every finding is a story with a story_type (risk, opportunity, capacity, policy_gap, success, operating_insight), a lens, evidence, and a counter-check.

## Architecture

- `data/raw/`: original event files, never modified.
- `data/parquet/`: generated query layer.
- `data/agency.duckdb`: fast local cold store.
- `data/findings/`: JSON findings and correlation output.
- `.neotoma/data/`: local Neotoma truth ledger.
- `state/`: schema profiles, manifests, run logs.

## Loop

1. Onboard datasets.
2. Profile schemas and file hashes.
3. Ask Codex (or the heuristic planner) to select runnable skills and reject unsupported ones, with reasons.
4. Run selected deterministic skills against DuckDB. Each finding is tagged with a story_type and lens.
5. Verify by replay.
6. Ask Codex (or the heuristic planner) for disconfirming checks and cautious entity clusters.
7. Ask Claude (or the heuristic story-shaper) to classify each finding into a story type and write the seven-field story packet: what_happened, why_it_matters, who_is_affected, evidence_summary, what_could_disprove, what_to_check_next, decision_enabled.
8. Promote plan, rejections, findings, checks, clusters, stories, and queue to local Neotoma.
9. Build the static HTML dashboard with three columns: risks, operating insight, opportunities.
10. Present only stories with provenance.

## Language Discipline

Use `review lead`, `candidate`, or `needs human review`. Frame each finding as a story, not an accusation.

Do not say fraud, corruption, illegal, or wrongdoing unless the dataset explicitly proves it and a human has verified it.

Story types are not all negative. Risk is one of six. Opportunity, success, capacity, policy gap, and operating insight matter as much. Pitch this as a public-interest story engine, not a fraud detector.

## Build Discipline

Keep the demo laptop-local. VPS sync is optional.

Do not make live internet, remote Neotoma, venue Wi-Fi, or live model latency critical to the pitch. Run the work first and present the generated HTML.

Do not load raw multi-thousand-row result sets into model context. Use schema, samples, counts, top-N summaries, and saved SQL.
