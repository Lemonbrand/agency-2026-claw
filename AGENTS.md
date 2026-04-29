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
3. Run skills against DuckDB.
4. Save findings with SQL and evidence.
5. Verify by replay.
6. Promote verified or reviewable findings to Neotoma.
7. Present only claims with provenance.

## Language Discipline

Use `review lead`, `candidate`, or `needs human review`.

Do not say fraud, corruption, illegal, or wrongdoing unless the dataset explicitly proves it and a human has verified it.

## Build Discipline

Keep the demo laptop-local. VPS sync is optional.

Do not make live internet, remote Neotoma, or venue Wi-Fi critical to the pitch.

Do not load raw multi-thousand-row result sets into model context. Use schema, samples, counts, top-N summaries, and saved SQL.
