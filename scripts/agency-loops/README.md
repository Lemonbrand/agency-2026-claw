# Agency 2026 — Parallel Loops

10 GLM 5.1 ralph loops, one per accountability challenge, running on the VPS in parallel tmux sessions. Each loop iterates aider against a `PROMPT.md` until its `research-brief.md` carries `<status>COMPLETE</status>` at the top, or it exhausts 12 iterations.

## Layout

```
agency-loops/
  STRUCTURE.md                       # the six-section research-brief shape (shared)
  ITERATE.md                         # iteration discipline (shared)
  KNOWN-DATA-ISSUES-NOTES.md         # data quality footguns excerpted (shared)
  run-template.sh                    # per-loop runner (copied in by orchestrate)
  orchestrate.sh                     # launch all 10 tmux sessions
  status.sh                          # snapshot all 10
  01-zombie-recipients/
    PROMPT.md
    research-brief.md                # the deliverable, iteratively authored
    progress.log                     # aider stdout + iteration markers
    run.sh                           # symlink/copy of run-template.sh
  02-ghost-capacity/
  ...
  10-adverse-media/
```

## VPS deployment

```bash
# from local repo
rsync -e "ssh -i ~/.ssh/id_ed25519_nanoclaw" -avz scripts/agency-loops/ \
  root@159.65.241.230:/opt/lemon-agency/

# launch
ssh -i ~/.ssh/id_ed25519_nanoclaw root@159.65.241.230 \
  "cd /opt/lemon-agency && ./orchestrate.sh"

# monitor
ssh -i ~/.ssh/id_ed25519_nanoclaw root@159.65.241.230 \
  "cd /opt/lemon-agency && ./status.sh"
```

## What success looks like

Each loop produces a `research-brief.md` with six sections, each grounded in real Canadian government data sources, each carrying the disconfirming check and the citation pack a journalist or auditor would need. The deliverable is not the analysis output (that is what LemonClaw does). The deliverable is the proof that an AI agent can, in parallel and at speed, produce structured research briefs covering ten hard accountability questions with jury-grade provenance.

The orchestrator (Claude on a 5-minute /loop) writes a roll-up after each cycle: per-loop iteration count, brief size, completion state, and the new patterns or sources surfaced.

## Stop conditions

- `<status>COMPLETE</status>` at the top of `research-brief.md` (success).
- 12 iterations without completion (graceful exhaust).
- Manual `tmux kill-session -t agency-<loop>` (operator override).
