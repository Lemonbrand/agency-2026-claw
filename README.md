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
./bin/agency plan --brain heuristic
./bin/agency run-plan
./bin/agency verify
./bin/agency disconfirm --brain heuristic
./bin/agency resolve-entities --brain heuristic
./bin/agency correlate
./bin/agency review --reviewer heuristic
./bin/agency promote
./bin/agency ui
```

Open `web/dashboard.html` in a browser.

## Event Workflow

1. Put provided datasets in `data/raw/`.
2. Run `./bin/agency onboard`.
3. Run `./bin/agency plan --brain codex`.
4. Run `./bin/agency run-plan`.
5. Run `./bin/agency verify`.
6. Run `./bin/agency disconfirm --brain codex`.
7. Run `./bin/agency resolve-entities --brain codex`.
8. Run `./bin/agency correlate`.
9. Run `./bin/agency review --reviewer claude`.
10. Use `./bin/agency promote` to write findings into the local Neotoma truth ledger.

The `heuristic` brain and reviewer exist for smoke tests. The demo path uses Codex as the planning brain and Claude as the skeptical second pass through their subscription CLIs.

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

For the full agentic demo, run from a trusted shell or expand `bin/nono.sh` to allow `~/.codex` and `~/.claude`. Codex and Claude subscription CLIs read local auth state.

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

## Agentic Loop

Codex is the investigator:

- reads the schema profile
- selects runnable skills
- rejects unsupported skills with reasons
- proposes disconfirming checks
- clusters surfaced entity names cautiously

DuckDB is the calculator. It runs deterministic SQL against the local data.

Claude is the reviewer. It challenges language and weak claims after the queue is built.

Neotoma is the audit ledger. It stores the plan, rejections, runs, findings, checks, clusters, review, and final queue.
