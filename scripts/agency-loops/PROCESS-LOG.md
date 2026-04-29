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

(Filled in by Claude via /loop cron.)
