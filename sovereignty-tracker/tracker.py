#!/usr/bin/env python3
"""Sovereignty cost + cross-border data tracker.

Pulls aider Cost lines from VPS progress.logs, reads manual entries for
Claude / Codex / direct API work, computes running totals + cross-border
data volume, and renders a static HTML dashboard.

Run repeatedly throughout the day. State accumulates across runs via
.state.json so totals persist between invocations.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / ".state.json"
MANUAL_PATH = ROOT / "manual-entries.jsonl"
DASHBOARD_PATH = ROOT / "dashboard.html"

VPS_USER = "root"
VPS_HOST = "159.65.241.230"
VPS_KEY = "~/.ssh/id_ed25519_nanoclaw"
VPS_LOOPS_PATH = "/opt/lemon-agency"

# Per-1M-token pricing (USD). All numbers as of April 2026.
# These are public list prices for the API-equivalent cost. Subscription users
# pay flat rate; the dashboard reports the API-equivalent so the magnitude is
# legible to a non-technical audience.
PRICING = {
    "z-ai/glm-5.1":         {"in": 0.55,  "out": 2.20,  "country": "US-routed (OpenRouter), CN-hosted (Z.ai)"},
    "openrouter/z-ai/glm-5.1": {"in": 0.55,  "out": 2.20,  "country": "US-routed (OpenRouter), CN-hosted (Z.ai)"},
    "claude-sonnet-4-6":    {"in": 3.00,  "out": 15.00, "country": "US (Anthropic)"},
    "claude-opus-4-7":      {"in": 15.00, "out": 75.00, "country": "US (Anthropic)"},
    "claude-opus-4-7[1m]":  {"in": 15.00, "out": 75.00, "country": "US (Anthropic, 1M context tier)"},
    "claude-haiku-4-5":     {"in": 1.00,  "out": 5.00,  "country": "US (Anthropic)"},
    "gpt-5.5":              {"in": 2.00,  "out": 16.00, "country": "US (OpenAI, subscription API-equivalent)"},
    "gpt-5.5-xhigh":        {"in": 2.00,  "out": 16.00, "country": "US (OpenAI, subscription API-equivalent)"},
    "gpt-5.2":              {"in": 1.25,  "out": 10.00, "country": "US (OpenAI)"},
    "gpt-5":                {"in": 1.25,  "out": 10.00, "country": "US (OpenAI)"},
    "codex":                {"in": 1.25,  "out": 10.00, "country": "US (OpenAI)"},
    "cohere-command":       {"in": 0.50,  "out": 1.50,  "country": "Canada (Cohere)"},
}

BYTES_PER_TOKEN = 4  # rough average for English tokens.


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {
        "first_seen": int(time.time()),
        "openrouter_calls_seen": [],
        "totals_by_model": {},
    }


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2))


def fetch_aider_cost_lines() -> list[str]:
    """SSH the VPS and grep all aider 'Tokens:...Cost:' lines from progress.logs."""
    cmd = (
        f"ssh -i {VPS_KEY} -o ConnectTimeout=8 {VPS_USER}@{VPS_HOST} "
        f'\'cd {VPS_LOOPS_PATH} && grep -h "^Tokens:.*Cost:" */progress.log 2>/dev/null\''
    )
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=20)
    except subprocess.CalledProcessError:
        return []
    except subprocess.TimeoutExpired:
        return []
    return [line for line in out.splitlines() if line.strip()]


def fetch_vps_bandwidth() -> dict | None:
    """Pull eth0 RX/TX bytes from the VPS."""
    cmd = (
        f"ssh -i {VPS_KEY} -o ConnectTimeout=8 {VPS_USER}@{VPS_HOST} "
        f"'awk \"/eth0:/ {{print \\$2, \\$10}}\" /proc/net/dev'"
    )
    try:
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=15).strip()
    except Exception:
        return None
    parts = out.split()
    if len(parts) != 2:
        return None
    return {"rx_bytes": int(parts[0]), "tx_bytes": int(parts[1])}


AIDER_LINE_RE = re.compile(
    r"Tokens:\s*([\d.]+)([km])?\s*sent,\s*([\d.]+)([km])?\s*received\.\s*Cost:\s*\$([\d.]+)\s*message"
)


def parse_aider_line(line: str) -> dict | None:
    m = AIDER_LINE_RE.search(line)
    if not m:
        return None
    sent_raw, sent_unit, recv_raw, recv_unit, cost = m.groups()
    sent = float(sent_raw) * (1000 if sent_unit == "k" else 1_000_000 if sent_unit == "m" else 1)
    recv = float(recv_raw) * (1000 if recv_unit == "k" else 1_000_000 if recv_unit == "m" else 1)
    return {
        "tokens_in": int(sent),
        "tokens_out": int(recv),
        "cost_usd": float(cost),
    }


def load_manual_entries() -> list[dict]:
    if not MANUAL_PATH.exists():
        return []
    out = []
    for line in MANUAL_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    p = PRICING.get(model)
    if not p:
        return 0.0
    return (tokens_in * p["in"] + tokens_out * p["out"]) / 1_000_000


def refresh_local_usage() -> None:
    """Refresh Claude/Codex local usage before aggregating dashboard totals."""
    poller = ROOT / "poll_local.py"
    if not poller.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(poller)],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=90,
            check=False,
        )
    except Exception:
        return


def aggregate(state: dict) -> dict:
    """Accumulate aider lines (idempotent via line hash) + manual entries.

    Returns: {totals_by_model, totals_overall, calls}

    NOTE: poll_local.py writes .openrouter-today.json with the authoritative daily $
    from OpenRouter's /auth/key endpoint. If that file exists we trust it as the
    OpenRouter total and use aider lines only for token-volume estimation.
    """
    aider_lines = fetch_aider_cost_lines()
    seen = set(state.get("openrouter_calls_seen", []))
    totals: dict[str, dict] = state.get("totals_by_model", {}).copy()

    or_authoritative = None
    try:
        _p = ROOT / ".openrouter-today.json"
        if _p.exists():
            or_authoritative = json.loads(_p.read_text())
    except Exception:
        or_authoritative = None

    new_count = 0
    for idx, line in enumerate(aider_lines):
        # idempotency: hash of (line + index) so identical lines that repeat are still counted.
        key = f"{idx}:{line}"
        if key in seen:
            continue
        parsed = parse_aider_line(line)
        if not parsed:
            continue
        model = "openrouter/z-ai/glm-5.1"
        bucket = totals.setdefault(
            model,
            {
                "calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cache_read_tokens": 0,
                "uncached_input_tokens": 0,
                "reasoning_tokens": 0,
                "cost_usd": 0.0,
                "country": PRICING[model]["country"],
            },
        )
        bucket["calls"] += 1
        bucket["tokens_in"] += parsed["tokens_in"]
        bucket["tokens_out"] += parsed["tokens_out"]
        bucket["uncached_input_tokens"] = bucket.get("uncached_input_tokens", 0) + parsed["tokens_in"]
        bucket["cost_usd"] += parsed["cost_usd"]
        seen.add(key)
        new_count += 1

    # Manual entries (Claude, Codex, etc.)
    for entry in load_manual_entries():
        key = f"manual:{entry.get('ts')}:{entry.get('model')}:{entry.get('tokens_in')}:{entry.get('tokens_out')}"
        if key in seen:
            continue
        model = entry.get("model", "unknown")
        tokens_in = int(entry.get("tokens_in", 0) or 0)
        tokens_out = int(entry.get("tokens_out", 0) or 0)
        cache_read = int(entry.get("cache_read_tokens", 0) or 0)
        uncached_in = int(entry.get("uncached_input_tokens", max(0, tokens_in - cache_read)) or 0)
        reasoning = int(entry.get("reasoning_tokens", 0) or 0)
        cost = entry.get("cost_usd")
        if cost is None:
            cost = estimate_cost(model, tokens_in, tokens_out)
        bucket = totals.setdefault(
            model,
            {
                "calls": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "cache_read_tokens": 0,
                "uncached_input_tokens": 0,
                "reasoning_tokens": 0,
                "cost_usd": 0.0,
                "country": PRICING.get(model, {}).get("country", "Unknown"),
            },
        )
        bucket["calls"] += int(entry.get("calls", 1) or 1)
        bucket["tokens_in"] += tokens_in
        bucket["tokens_out"] += tokens_out
        bucket["cache_read_tokens"] = bucket.get("cache_read_tokens", 0) + cache_read
        bucket["uncached_input_tokens"] = bucket.get("uncached_input_tokens", 0) + uncached_in
        bucket["reasoning_tokens"] = bucket.get("reasoning_tokens", 0) + reasoning
        bucket["cost_usd"] += float(cost)
        seen.add(key)
        new_count += 1

    state["openrouter_calls_seen"] = sorted(seen)[-2000:]  # cap memory
    state["totals_by_model"] = totals
    state["last_run_ts"] = int(time.time())
    state["last_run_new_calls"] = new_count

    # If OpenRouter /auth/key gave us the authoritative daily $, override the aider-derived bucket.
    if or_authoritative and "usage_today_usd" in or_authoritative:
        # Token estimate from $ assuming 70% of spend is input @ $0.55/M and 30% output @ $2.20/M for GLM 5.1.
        d = float(or_authoritative["usage_today_usd"])
        est_in = int((d * 0.70) / 0.55 * 1_000_000)
        est_out = int((d * 0.30) / 2.20 * 1_000_000)
        totals["openrouter/z-ai/glm-5.1"] = {
            "calls": totals.get("openrouter/z-ai/glm-5.1", {}).get("calls", 0),
            "tokens_in": est_in,
            "tokens_out": est_out,
            "cache_read_tokens": 0,
            "uncached_input_tokens": est_in,
            "reasoning_tokens": 0,
            "cost_usd": d,
            "country": PRICING["openrouter/z-ai/glm-5.1"]["country"],
            "_authoritative": True,
        }
        state["totals_by_model"] = totals

    bw = fetch_vps_bandwidth()
    if bw:
        state["vps_bandwidth"] = bw

    return state


def render_dashboard(state: dict) -> str:
    totals = state.get("totals_by_model", {})

    sum_calls = sum(b["calls"] for b in totals.values())
    sum_in = sum(b["tokens_in"] for b in totals.values())
    sum_out = sum(b["tokens_out"] for b in totals.values())
    sum_cache = sum(b.get("cache_read_tokens", 0) for b in totals.values())
    sum_uncached_in = sum(b.get("uncached_input_tokens", max(0, b["tokens_in"] - b.get("cache_read_tokens", 0))) for b in totals.values())
    sum_cost = sum(b["cost_usd"] for b in totals.values())
    bytes_to_us = (sum_uncached_in + sum_out) * BYTES_PER_TOKEN

    bw = state.get("vps_bandwidth", {})
    rx_gb = bw.get("rx_bytes", 0) / 1e9
    tx_gb = bw.get("tx_bytes", 0) / 1e9

    # Sovereignty extrapolation: if Canada ran this every night across every department
    # 23 federal departments + 13 provincial+territorial gov × 100 ministries each ≈ 1500 daily runs.
    # Budget multiplier: today's spend × 1500 × 365 = annual flat-fed cost.
    canada_scale = sum_cost * 1500 * 365

    rows = []
    for model, b in sorted(totals.items(), key=lambda kv: -kv[1]["cost_usd"]):
        cache_read = b.get("cache_read_tokens", 0)
        uncached_in = b.get("uncached_input_tokens", max(0, b["tokens_in"] - cache_read))
        reasoning = b.get("reasoning_tokens", 0)
        rows.append(
            f"<tr><td>{model}</td>"
            f"<td>{b['country']}</td>"
            f"<td>{b['calls']:,}</td>"
            f"<td>{b['tokens_in']:,}</td>"
            f"<td>{cache_read:,}</td>"
            f"<td>{uncached_in:,}</td>"
            f"<td>{b['tokens_out']:,}</td>"
            f"<td>{reasoning:,}</td>"
            f"<td>${b['cost_usd']:.4f}</td></tr>"
        )

    last_run = time.strftime("%H:%M:%S %Z", time.localtime(state.get("last_run_ts", 0)))
    first_seen = time.strftime("%H:%M:%S %Z", time.localtime(state.get("first_seen", 0)))

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sovereignty cost tracker — Agency 2026</title>
<style>
  :root {{
    --ink: #18130c; --paper: #fbf7ed; --panel: #fff; --line: #e0d6c1;
    --muted: #6b6354; --gold: #c47a1d; --red: #993f3f; --green: #2c684f; --blue: #2a5277;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif; background: var(--paper); color: var(--ink); line-height: 1.5; }}
  header.top {{ padding: 28px 32px 22px; background: var(--ink); color: var(--paper); }}
  header.top h1 {{ margin: 0; font-size: 30px; font-weight: 800; letter-spacing: -0.01em; }}
  header.top p {{ margin: 8px 0 0; color: #f1ddb6; max-width: 920px; font-size: 15px; }}
  main {{ padding: 24px 32px 64px; max-width: 1280px; margin: 0 auto; }}
  .summary {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-bottom: 22px; }}
  .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 16px; }}
  .metric strong {{ display: block; font-size: 26px; line-height: 1; }}
  .metric span {{ display: block; margin-top: 6px; color: var(--muted); font-size: 13px; }}
  .metric.alert {{ border-left: 4px solid var(--red); }}
  table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; margin-bottom: 22px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--line); font-size: 13px; vertical-align: top; }}
  th {{ background: var(--paper); color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }}
  td:first-child {{ font-weight: 600; }}
  .policy {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 22px; margin-bottom: 18px; }}
  .policy h2 {{ margin: 0 0 8px; font-size: 20px; }}
  .policy p {{ margin: 0 0 12px; }}
  .policy ul {{ margin: 0; padding-left: 22px; }}
  .policy li {{ margin: 6px 0; }}
  .extrap {{ background: #fff5e0; border: 1px solid var(--gold); border-left: 5px solid var(--gold); padding: 16px 20px; border-radius: 10px; margin-bottom: 18px; }}
  .extrap strong {{ font-size: 22px; }}
  .meta {{ color: var(--muted); font-size: 12px; }}
  @media (max-width: 800px) {{ .summary {{ grid-template-columns: 1fr 1fr; }} }}
</style>
</head>
<body>
<header class="top">
  <h1>Where the data is going. Who's getting paid. Why it matters.</h1>
  <p>A live tracker for the LemonClaw demo at Agency 2026. Every API call our agents make today is to a US-routed endpoint. Every byte of every prompt and every response crosses the border. The dollar cost is small. The policy cost is not.</p>
</header>
<main>
  <section class="summary">
    <div class="metric"><strong>{sum_calls:,}</strong><span>model calls / turns tracked today</span></div>
    <div class="metric alert"><strong>{(sum_in + sum_out)/1000:.1f}k</strong><span>tokens processed by US-routed endpoints</span></div>
    <div class="metric"><strong>{sum_cache/1000:.1f}k</strong><span>cached input tokens reused server-side</span></div>
    <div class="metric"><strong>{bytes_to_us/1024:.1f} KiB</strong><span>estimated uncached token bytes crossing border</span></div>
    <div class="metric"><strong>${sum_cost:.4f}</strong><span>API-equivalent spend today</span></div>
  </section>

  <h2>By provider</h2>
  <table>
    <thead><tr><th>Model</th><th>Routing / Hosting</th><th>Calls</th><th>Input</th><th>Cached input</th><th>Uncached input</th><th>Output</th><th>Reasoning out</th><th>API-equiv $</th></tr></thead>
    <tbody>{''.join(rows) or '<tr><td colspan="9" class="meta">No data yet.</td></tr>'}</tbody>
  </table>

  <h2>VPS bandwidth (rough proxy for non-API traffic)</h2>
  <table>
    <thead><tr><th>Direction</th><th>GB</th><th>Note</th></tr></thead>
    <tbody>
      <tr><td>VPS RX (incoming)</td><td>{rx_gb:.2f}</td><td>OpenRouter responses, GitHub clones, npm, Granola transcripts, Postgres replies, etc.</td></tr>
      <tr><td>VPS TX (outgoing)</td><td>{tx_gb:.2f}</td><td>OpenRouter prompts, dashboard serves, Postgres queries, Neotoma writes, etc.</td></tr>
    </tbody>
  </table>

  <div class="extrap">
    Extrapolation: <strong>${canada_scale/1e6:.1f}M / year</strong> if every Canadian federal + provincial + territorial ministry ran a workload of today's shape, nightly.
    <p class="meta" style="margin-top:6px;">Math: today's spend × ~1,500 ministries × 365 nights. The flat number is small per ministry; the systemic number is the policy story. Every dollar leaves the country at API rates. Every byte crosses the border.</p>
  </div>

  <div class="policy">
    <h2>The policy push</h2>
    <p>This is not a fundraiser. It is a critical-infrastructure problem the way water and power are critical-infrastructure problems. Token spend on US-routed inference is the only thing keeping our stack defended right now, until baremetal sovereign infra lands. That transition will take a decade or more. The waitlists for the hardware that closes the gap are 18-24 months. The decision window is now.</p>
    <h3 style="margin-top:14px;">Federal asks</h3>
    <ul>
      <li>National AI compute strategy with explicit Blackwell / MI300X allocation, paired with the existing Pan-Canadian AI Strategy.</li>
      <li>Treasury Board sovereign-cloud framework: list approved Canadian-hosted inference providers (Cohere, Canadian DC operators) and require federal departments to default to them where feasible.</li>
      <li>Innovation, Science and Economic Development Canada (ISED) to coordinate inter-departmental GPU procurement at federal scale rather than per-ministry.</li>
    </ul>
    <h3 style="margin-top:14px;">Provincial asks (Alberta as the obvious lead)</h3>
    <ul>
      <li>Province-led data-centre siting with hydro / flare-gas / nuclear power agreements. Alberta's existing data-centre cluster around Calgary is a natural foundation.</li>
      <li>Provincial-scale GPU pre-orders. The federal procurement window is large; provincial windows can move faster.</li>
      <li>Alberta + AB AI Institute (AMII) joint sovereign-inference benchmark suite. Test Cohere, Canadian-hosted variants, and US providers head-to-head on accountability workloads like the ten Agency 2026 challenges.</li>
    </ul>
    <h3 style="margin-top:14px;">Local asks</h3>
    <ul>
      <li>Municipal co-location offers: Calgary, Edmonton, Toronto, Montreal, Halifax all have power + cooling capacity if zoning unlocks. Tax credits for sovereign-DC anchor tenants.</li>
      <li>Municipal data sovereignty by-laws: any municipal vendor running AI on resident data must disclose hosting location and routing.</li>
    </ul>
    <h3 style="margin-top:14px;">Why now (the Mythos-class context)</h3>
    <p>Frontier agentic models are at the point where attack surface scales with capability. Token-spend rate-limiting and monitored API endpoints are the temporary defence. The durable defence is baremetal infrastructure with controlled attack surface — sovereign datacentres, Canadian-hosted models, audited supply chain. That posture takes a decade to stand up and the GPU waitlists are the gating step. Get on them now.</p>
  </div>

  <p class="meta">Tracker started {first_seen}. Last refreshed {last_run}. Data sources: aider <code>Cost:</code> lines from <code>/opt/lemon-agency/*/progress.log</code> on the LemonClaw VPS, local Claude Code JSONL usage, and local Codex rollout <code>token_count</code> counters from <code>~/.codex/sessions</code>. Codex cached input is counted separately: it is real model-side work, but not all of it crosses the network again. Reasoning tokens are reported as a subset of output where the local cache exposes them. Bandwidth is whole-VPS and intentionally rough.</p>
</main>
</body>
</html>
"""


def main() -> int:
    refresh_local_usage()
    state = load_state()
    state = aggregate(state)
    save_state(state)
    DASHBOARD_PATH.write_text(render_dashboard(state))

    totals = state.get("totals_by_model", {})
    print(f"[{time.strftime('%H:%M:%S')}] new calls: {state.get('last_run_new_calls', 0)}")
    print(f"  total models tracked: {len(totals)}")
    sum_cost = sum(b["cost_usd"] for b in totals.values())
    sum_calls = sum(b["calls"] for b in totals.values())
    sum_tokens = sum(b["tokens_in"] + b["tokens_out"] for b in totals.values())
    print(f"  total calls: {sum_calls:,}")
    print(f"  total tokens: {sum_tokens:,}")
    print(f"  API-equiv spend: ${sum_cost:.4f}")
    print(f"  dashboard: {DASHBOARD_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
