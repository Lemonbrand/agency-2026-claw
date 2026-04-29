# Process Log — 10 Parallel Agency 2026 Research Loops

**Goal**: not to solve the ten challenges, but to prove that AI can attack them in parallel, at speed, with structured output and jury-grade citations.

**Stack**: aider + GLM 5.1 (`z-ai/glm-5.1`) via OpenRouter, one tmux session per loop, hosted on the LemonClaw VPS (159.65.241.230). Per-loop output: `research-brief.md`, six sections, source-cited, with a `<status>COMPLETE</status>` self-signal. Per-loop budget: 12 iterations max.

**Observability**: `status.sh` snapshots all 10 loops in one terminal. The orchestrator (Claude on a 5-minute /loop cron) writes roll-ups here.

## Timeline

### T+0:00 — 09:??:?? ET — scaffold

10 challenge directories created locally under `scripts/agency-loops/`. Shared `STRUCTURE.md` + `ITERATE.md` + `KNOWN-DATA-ISSUES-NOTES.md` for the discipline; per-challenge `PROMPT.md` with domain priors hand-written from the GovAlta repo's KNOWN-DATA-ISSUES + dataset documentation.

### T+0:15 — VPS infra check

`aider`, `tmux`, `jq`, and `/etc/lemonclaw/openrouter.env` all already present on the VPS from prior delegate-to-ralph-vps runs. No bootstrap needed.

### T+0:18 — rsync to VPS

42 KB of scaffold pushed to `/opt/lemon-agency/`.

### T+0:20 — single-loop smoke test

Loop 01 (Zombie Recipients) ran one iteration end-to-end. First-iteration brief produced 10.6 KB of structured content with real CRA T3010 field codes, F-3 mitigation called out explicitly, and Corporations Canada cited as the missing-data source. Decision: launch the rest.

### T+0:22 — orchestrate

`orchestrate.sh` launched ten tmux sessions. Each session runs a fresh `run.sh` against its own challenge's PROMPT.md. All ten alive at first status check.

### T+0:23 — first status snapshot

```
loop                              tmux        iter    status      brief_KB
01-zombie-recipients              running     3       (residue)   10.6
02-ghost-capacity                 running     1       active      0.3
03-funding-loops                  running     1       active      0.3
04-sole-source-amendment          running     1       active      0.3
05-vendor-concentration           running     1       active      0.3
06-related-parties                running     1       active      0.3
07-policy-misalignment            running     1       active      0.3
08-duplicative-funding            running     1       active      0.3
09-contract-intelligence          running     1       active      0.3
10-adverse-media                  running     1       active      0.3
```

Loop 01 carries iter=3 because the smoke test wrote progress markers and the new launch resumed against the same dir. Functionally fine — the loop will continue iterating up to 12.

### T+0:?? — roll-ups every 5 minutes

### Cycle 1 — 09:28 ET / 13:28 UTC

Three loops self-signaled COMPLETE at iteration 6 (~12 minutes after launch): **03-funding-loops**, **05-vendor-concentration**, **09-contract-intelligence**. Six loops are still iterating. One loop (02-ghost-capacity) hung mid-iteration 1 with aider attached but silent for 13 minutes; killed and restarted clean. Spot-check rotation hit 02 right when it was dead, which is the observation worth logging — failure mode is "tmux running, aider quiet" not "tmux crashed."

```
loop                              tmux        iter   status      brief_KB
01-zombie-recipients              running     11     (smoke residue)  13.4
02-ghost-capacity                 restarted   0      relaunched       0
03-funding-loops                  running     11     DONE@iter6       16.6
04-sole-source-amendment          running     3      slow             6.7
05-vendor-concentration           running     11     DONE@iter6       16.4
06-related-parties                running     9      active          16.0
07-policy-misalignment            running     9      active          10.0
08-duplicative-funding            running     11     active          12.7
09-contract-intelligence          running     11     DONE@iter6       14.4
10-adverse-media                  running     9      active          15.3
```

Sovereignty tracker delta this cycle: **+38 calls / +359k tokens / +$0.80**. Running totals: **125 calls / 1.07M tokens / $8.49 API-equiv**. The CRA loop_universe precomputation is the most-cited resource across loops surveyed so far (03 leans on it directly, 06 references it for governance overlays). Next cycle: rotate to 03 to spot-check a COMPLETED brief.

### Inter-cycle event — 09:28 ET / 13:28 UTC — Codex verification layer enters the architecture

Simon's Codex (with direct SQL DB access) just published `VERIFIED_SCHEMA.md` (434 lines) and `CORRECTION_PASS.md` (118 lines) to `/opt/lemon-agency/`, plus modified `run-template.sh` so every subsequent aider call reads both as ground truth. The schema doc explicitly names the hallucinated references the loops had been citing (`fed.vw_agreement_current`, `cra.t3010`, `cra.loop_universe.risk_score`, etc.) and supplies the F-3-safe CTE workaround. The correction pass forces every brief to add a `Current executable status: RUNNABLE_NOW | RUNNABLE_WITH_EXTRA_MATERIALIZATION | NEEDS_EXTERNAL_DATA | RESEARCH_ONLY` line and replace dead references.

This is the multi-brain pattern landing in real time:

- **GLM 5.1**: parallel cheap-fast generation (10 loops, ~$0.02 / iteration).
- **GPT-5.2 (Codex)**: SQL-grounded verification + curation of source-of-truth.
- **Claude (this orchestrator)**: meta-narrative + observability.

Each is doing the job it's actually good at. The hallucination gap I called out in last night's critique just closed. Logged Codex's oversight session in the sovereignty tracker (~255k tokens, ~$0.69 API-equivalent). Running totals after the manual entry: **202 calls / 1.73M tokens / $10.01 API-equiv** — first dollar threshold crossed.

Files mirrored back to local: `scripts/agency-loops/VERIFIED_SCHEMA.md`, `scripts/agency-loops/CORRECTION_PASS.md`, updated `run-template.sh`. They will travel with the next push to the public repo.
