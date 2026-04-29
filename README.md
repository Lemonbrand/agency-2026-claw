# Agency 2026 Claw

Local-first accountability workbench for the Agency 2026 hackathon.

The shape:

- DuckDB handles large datasets fast.
- Neotoma records what the agents believed, why, and how to replay it.
- Claw skills turn raw rows into reviewable findings.
- `nono.sh` runs agents in a scoped sandbox.

This repo is designed to run from a laptop at the event. No VPS dependency in the demo path.

## Quick Start

```bash
./scripts/bootstrap.sh
./scripts/create-demo-data.py
./bin/agency onboard
./bin/agency run vendor-concentration
./bin/agency run amendment-creep
./bin/agency run related-parties
./bin/agency correlate
./bin/agency verify
./bin/agency promote
./bin/agency ui
```

Open `web/dashboard.html` in a browser.

## Event Workflow

1. Put provided datasets in `data/raw/`.
2. Run `./bin/agency onboard`.
3. Run the reliable SQL skills first:
   - `vendor-concentration`
   - `amendment-creep`
4. Run the hero graph skill:
   - `related-parties`
5. Run `./bin/agency correlate`.
6. Run `./bin/agency verify`.
7. Use `./bin/agency promote` to write findings into the local Neotoma truth ledger.

## Local Neotoma

This repo uses its own Neotoma package and data directory:

- runtime: `.runtime/neotoma/`
- data: `.neotoma/data/`
- tenant: `agency-2026-local`

Use:

```bash
./scripts/neotoma.sh entities list --type finding --user-id agency-2026-local
```

The wrapper unsets Simon's global `NEOTOMA_API_ONLY` so local offline writes work.

## Nono

Start an agent in this repo with:

```bash
./bin/nono.sh claude
```

Or run a command:

```bash
./bin/nono.sh ./bin/agency onboard
```

The sandbox allows this repo, reads `~/lemon` for reference patterns, and allows the local Neotoma/dashboard ports.

## What Counts As Truth

No finding is trusted because a model said it.

A finding is trusted when it has:

- source file hash
- table profile
- replayable SQL
- evidence rows or aggregation trail
- verifier status
- human review status

The model proposes. DuckDB checks. Neotoma remembers.
