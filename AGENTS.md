# Agency 2026 Claw Instructions

This repo is a local-first hackathon environment.

Core rule: optimize for auditable truth, not demo magic.

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
3. Ask Codex to select runnable skills and reject unsupported ones.
4. Run selected deterministic skills against DuckDB.
5. Verify by replay.
6. Ask Codex for disconfirming checks and cautious entity clusters.
7. Ask Claude for skeptical second-pass review.
8. Promote plan, rejections, findings, checks, clusters, review, and queue to Neotoma.
9. Present only claims with provenance.

## Language Discipline

Use `review lead`, `candidate`, or `needs human review`.

Do not say fraud, corruption, illegal, or wrongdoing unless the dataset explicitly proves it and a human has verified it.

## Build Discipline

Keep the demo laptop-local. VPS sync is optional.

Do not make live internet, remote Neotoma, or venue Wi-Fi critical to the pitch.

Do not load raw multi-thousand-row result sets into model context. Use schema, samples, counts, top-N summaries, and saved SQL.
