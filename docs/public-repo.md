# Public Repo Notes

This repository is safe to publish as a public technical artifact because it tracks the system and not event data.

## Committed

- source code
- skill declarations
- scripts
- docs
- empty data directories with `.gitkeep`
- `.env.example`

## Ignored

- `.env`
- `.venv/`
- `.runtime/`
- `.neotoma/`
- raw datasets
- generated Parquet files
- DuckDB files
- generated findings
- generated state JSON
- generated HTML dashboard
- Python bytecode

## Why Generated Outputs Are Ignored

The public repo should show how the loop works.

It should not accidentally publish:

- event-provided datasets
- local Neotoma state
- model outputs from a private run
- generated dashboards containing real findings

For public storytelling, regenerate the demo with synthetic data:

```bash
./scripts/create-demo-data.py
make presentation
```

## Suggested GitHub Description

Local-first agentic audit workbench for turning large public-sector datasets into replayable review leads.

## Suggested Topics

- ai-agents
- audit
- duckdb
- public-sector
- accountability
- hackathon
- data-governance
- local-first
