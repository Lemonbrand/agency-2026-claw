# Sovereignty Cost Tracker

Live tracker for what we spent and where the bytes went during Agency 2026. The dollar number is small. The policy story is large.

## What it tracks

| Source | How | Precision |
| --- | --- | --- |
| OpenRouter (GLM 5.1 via aider on the VPS) | `Tokens:...Cost:` lines from `/opt/lemon-agency/*/progress.log` over SSH | Exact, from aider |
| Claude (subscription) | `poll_local.py` parses `~/.claude/projects/*/*.jsonl` usage counters, including cache reads/writes | Exact local cache counters, API-equivalent cost |
| Codex (subscription) | `poll_local.py` parses `~/.codex/sessions/**/rollout-*.jsonl` `token_count` events and writes the aggregate to `manual-entries.jsonl` | Exact local rollout counters, including cached input |
| VPS bandwidth | `eth0` RX/TX from `/proc/net/dev` | Whole-VPS, over-counts US share |

## Run

```bash
./tracker.py                     # one-shot refresh of dashboard.html
./poll_local.py                  # optional: refresh Claude/Codex local counters only
```

`tracker.py` now runs `poll_local.py` first, then renders `dashboard.html`. The Claude /loop monitor on a 5-min cron can keep calling `tracker.py`; Codex totals will update from the local rollout cache each time.

## Why the API-equivalent rate

Subscriptions hide the marginal cost. The argument we make to ministers is: this is what every byte of this work would cost at full API rates, and that scaled across every department becomes the policy story. Subscription revenue still flows to the same US providers. The point is not "save money" — it is "see the dependency."

## Read the dashboard

Open `dashboard.html` (or `web/sovereignty.html` for the LemonClaw-mirrored version). Top of page: total calls, tokens to US, bytes across the border, API-equivalent spend. Middle: per-provider table. Bottom: the policy push, federal + provincial + local + Mythos-class context.

## Manual entry — quick reference

Append one JSON object per line to `manual-entries.jsonl` for providers that do not have a poller:

```json
{"ts":"2026-04-29T11:30:00-04:00","provider":"codex","model":"gpt-5.2","tokens_in":80000,"tokens_out":12000,"calls":8,"purpose":"SQL exploration on fed.grants_contributions","destination_country":"US","subscription_paid":true}
```

If `cost_usd` is omitted the tracker fills in via the PRICING table in `tracker.py`. If your model isn't in PRICING, supply `cost_usd` directly.

For Claude and Codex, do not hand-edit the generated entries. `poll_local.py` owns them and strips/replaces entries where `provider` is `claude` or `codex`.

## What this tracker is not

It is not an ad against any vendor. The vendors are excellent and the work would not be possible without them. It is a measurement of the dependency, presented honestly so the audience can see the size of the lift required to develop sovereign equivalents and the timeline of the GPU procurement that gates that work.
