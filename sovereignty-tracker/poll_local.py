#!/usr/bin/env python3
"""Poll local Claude Code + Codex CLI logs for real token usage today.

Replaces the rough manual estimates in manual-entries.jsonl with precise
per-message accounting parsed from disk:

- Claude Code: ~/.claude/projects/*/[*.jsonl] — every assistant turn carries
  message.usage with input/output/cache_creation/cache_read tokens.
- Codex CLI: ~/.codex/logs_2.sqlite — live SSE stream including
  response.completed events with usage; plus ~/.codex/sessions/<date>/*.jsonl
  for historical rollouts.

Writes a per-source summary JSON to .real-usage.json and emits one manual-entry
per source so the main tracker.py picks it up.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

HOME = Path.home()
TRACKER_DIR = Path(__file__).resolve().parent
LOCAL_TZ = ZoneInfo(os.environ.get("SOVEREIGNTY_TRACKER_TZ", "America/Toronto"))
TODAY_DATE = dt.datetime.now(LOCAL_TZ).date()
TODAY = TODAY_DATE.isoformat()
DAY_START = dt.datetime.combine(TODAY_DATE, dt.time.min, tzinfo=LOCAL_TZ)
DAY_END = DAY_START + dt.timedelta(days=1)
TODAY_EPOCH_START = int(DAY_START.timestamp())
TODAY_EPOCH_END = int(DAY_END.timestamp())

# Anthropic list pricing (per 1M tokens). Cache reads are 0.1x; 5m cache writes are 1.25x; 1h cache writes are 2x.
CLAUDE_PRICING = {
    "claude-opus-4-7":    {"in": 15.00, "out": 75.00, "cache_5m": 18.75, "cache_1h": 30.00, "cache_read": 1.50},
    "claude-opus-4-7-1m": {"in": 15.00, "out": 75.00, "cache_5m": 18.75, "cache_1h": 30.00, "cache_read": 1.50},
    "claude-sonnet-4-6":  {"in": 3.00,  "out": 15.00, "cache_5m": 3.75,  "cache_1h": 6.00,  "cache_read": 0.30},
    "claude-haiku-4-5":   {"in": 1.00,  "out": 5.00,  "cache_5m": 1.25,  "cache_1h": 2.00,  "cache_read": 0.10},
}

# OpenAI list pricing for the GPT-5 family. Cached input is 0.1x.
# gpt-5.5 figures are estimated until OpenAI publishes; xhigh reasoning is
# billed as output tokens, so reasoning-heavy sessions skew output cost up.
OPENAI_PRICING = {
    "gpt-5.5":            {"in": 2.00, "out": 16.00, "cache_read": 0.20},  # ESTIMATED
    "gpt-5.5-xhigh":      {"in": 2.00, "out": 16.00, "cache_read": 0.20},  # ESTIMATED
    "gpt-5.2":            {"in": 1.25, "out": 10.00, "cache_read": 0.125},
    "gpt-5":              {"in": 1.25, "out": 10.00, "cache_read": 0.125},
    "gpt-5-mini":         {"in": 0.25, "out": 2.00,  "cache_read": 0.025},
}


def normalize_claude_model(raw: str) -> str:
    if not raw:
        return "claude-opus-4-7"
    raw = raw.lower()
    if "opus" in raw:
        if "1m" in raw:
            return "claude-opus-4-7-1m"
        return "claude-opus-4-7"
    if "sonnet" in raw:
        return "claude-sonnet-4-6"
    if "haiku" in raw:
        return "claude-haiku-4-5"
    return "claude-opus-4-7"


def normalize_openai_model(raw: str) -> str:
    if not raw:
        return "gpt-5.5"
    raw = raw.lower()
    if "mini" in raw:
        return "gpt-5-mini"
    if "5.5" in raw or "5-5" in raw:
        return "gpt-5.5"
    if "5.2" in raw:
        return "gpt-5.2"
    if raw.startswith("gpt-5") or "gpt5" in raw:
        # Default to gpt-5.5 since that is what Simon is currently invoking via Codex CLI.
        return "gpt-5.5"
    return "gpt-5.5"


def parse_claude_jsonl(path: Path) -> dict[str, Any] | None:
    """Sum today's usage from a Claude Code session JSONL."""
    if not path.exists():
        return None
    if path.stat().st_size == 0:
        return None
    if path.stat().st_mtime < TODAY_EPOCH_START:
        return None

    by_model: dict[str, dict[str, int]] = {}
    n_messages = 0
    earliest = latest = None

    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "assistant":
                continue
            ts = obj.get("timestamp") or obj.get("ts")
            if ts:
                try:
                    msg_date = ts[:10]
                except Exception:
                    msg_date = ""
                if msg_date != TODAY:
                    continue
                if earliest is None or ts < earliest:
                    earliest = ts
                if latest is None or ts > latest:
                    latest = ts

            msg = obj.get("message") or {}
            usage = msg.get("usage") or {}
            if not usage:
                continue
            model_raw = msg.get("model") or obj.get("model") or ""
            model = normalize_claude_model(model_raw)
            bucket = by_model.setdefault(
                model,
                {"input": 0, "output": 0, "cache_create_5m": 0, "cache_create_1h": 0, "cache_read": 0, "messages": 0},
            )
            bucket["input"] += int(usage.get("input_tokens", 0) or 0)
            bucket["output"] += int(usage.get("output_tokens", 0) or 0)
            cache_create = usage.get("cache_creation") or {}
            bucket["cache_create_5m"] += int(cache_create.get("ephemeral_5m_input_tokens", 0) or 0)
            bucket["cache_create_1h"] += int(cache_create.get("ephemeral_1h_input_tokens", 0) or 0)
            # Some legacy events only have cache_creation_input_tokens at top level
            if not cache_create:
                bucket["cache_create_5m"] += int(usage.get("cache_creation_input_tokens", 0) or 0)
            bucket["cache_read"] += int(usage.get("cache_read_input_tokens", 0) or 0)
            bucket["messages"] += 1
            n_messages += 1

    if n_messages == 0:
        return None

    summary = {
        "session_file": str(path),
        "messages": n_messages,
        "earliest_ts": earliest,
        "latest_ts": latest,
        "by_model": by_model,
    }
    return summary


def cost_for_claude(by_model: dict[str, dict[str, int]]) -> float:
    cost = 0.0
    for model, b in by_model.items():
        p = CLAUDE_PRICING.get(model, CLAUDE_PRICING["claude-opus-4-7"])
        cost += b["input"] * p["in"] / 1e6
        cost += b["output"] * p["out"] / 1e6
        cost += b["cache_create_5m"] * p["cache_5m"] / 1e6
        cost += b["cache_create_1h"] * p["cache_1h"] / 1e6
        cost += b["cache_read"] * p["cache_read"] / 1e6
    return cost


def claude_total() -> dict[str, Any]:
    """Walk all Claude Code session JSONLs touched today, aggregate by model."""
    base = HOME / ".claude" / "projects"
    sessions: list[dict[str, Any]] = []
    by_model_total: dict[str, dict[str, int]] = {}
    for path in base.rglob("*.jsonl"):
        s = parse_claude_jsonl(path)
        if not s:
            continue
        sessions.append({"file": str(path), "messages": s["messages"], "earliest": s["earliest_ts"], "latest": s["latest_ts"]})
        for model, b in s["by_model"].items():
            agg = by_model_total.setdefault(
                model,
                {"input": 0, "output": 0, "cache_create_5m": 0, "cache_create_1h": 0, "cache_read": 0, "messages": 0},
            )
            for k, v in b.items():
                agg[k] = agg.get(k, 0) + v
    return {"sessions": sessions, "by_model": by_model_total, "cost_usd": cost_for_claude(by_model_total)}


def poll_openrouter() -> dict[str, Any]:
    """Pull authoritative daily / monthly $ from OpenRouter /auth/key endpoint via the VPS key."""
    try:
        import subprocess
        cmd = (
            "ssh -i ~/.ssh/id_ed25519_nanoclaw -o ConnectTimeout=8 root@159.65.241.230 "
            "'set -a; source /etc/lemonclaw/openrouter.env; set +a; "
            "curl -s -H \"Authorization: Bearer $OPENROUTER_API_KEY\" https://openrouter.ai/api/v1/auth/key'"
        )
        out = subprocess.check_output(cmd, shell=True, text=True, timeout=20)
        data = json.loads(out).get("data", {})
        return {
            "usage_today_usd": float(data.get("usage_daily", 0) or 0),
            "usage_week_usd": float(data.get("usage_weekly", 0) or 0),
            "usage_month_usd": float(data.get("usage_monthly", 0) or 0),
            "usage_total_usd": float(data.get("usage", 0) or 0),
        }
    except Exception as exc:
        return {"error": str(exc)}


TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens", "total_tokens")


def parse_iso_ts(raw: str) -> dt.datetime | None:
    if not raw:
        return None
    try:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(LOCAL_TZ)


def empty_usage() -> dict[str, int]:
    return {k: 0 for k in TOKEN_KEYS}


def usage_delta(last: dict[str, Any], baseline: dict[str, Any]) -> dict[str, int]:
    return {k: max(0, int(last.get(k, 0) or 0) - int(baseline.get(k, 0) or 0)) for k in TOKEN_KEYS}


def parse_codex_rollout(path: Path) -> dict[str, Any] | None:
    """Read one Codex rollout JSONL and compute today's usage delta.

    Codex writes authoritative cumulative token counters as event_msg/token_count
    events. For a thread that spans midnight, count only the delta between the
    last counter before local midnight and the latest counter today.
    """
    if not path.exists() or path.stat().st_size == 0:
        return None

    baseline = empty_usage()
    last_today: dict[str, int] | None = None
    latest_total: dict[str, int] | None = None
    first_today_ts = latest_today_ts = None
    unique_totals_today: set[tuple[int, int, int, int, int]] = set()

    try:
        lines = path.open(errors="ignore")
    except OSError:
        return None

    with lines:
        for line in lines:
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "event_msg":
                continue
            payload = obj.get("payload") or {}
            if payload.get("type") != "token_count":
                continue
            info = payload.get("info") or {}
            total = info.get("total_token_usage") or {}
            if not total:
                continue
            ts = parse_iso_ts(obj.get("timestamp", ""))
            if not ts:
                continue

            normalized = {k: int(total.get(k, 0) or 0) for k in TOKEN_KEYS}
            latest_total = normalized
            if ts < DAY_START:
                baseline = normalized
                continue
            if ts >= DAY_END:
                break

            last_today = normalized
            if first_today_ts is None:
                first_today_ts = ts.isoformat()
            latest_today_ts = ts.isoformat()
            unique_totals_today.add(tuple(normalized[k] for k in TOKEN_KEYS))

    if not last_today:
        return None

    delta = usage_delta(last_today, baseline)
    if delta["total_tokens"] <= 0 and delta["input_tokens"] <= 0 and delta["output_tokens"] <= 0:
        return None

    return {
        "rollout_path": str(path),
        "first_today_ts": first_today_ts,
        "latest_today_ts": latest_today_ts,
        "calls_today": len(unique_totals_today),
        "baseline_before_today": baseline,
        "latest_today_total": last_today,
        "latest_thread_total": latest_total or last_today,
        "delta_today": delta,
    }


def load_codex_threads_touched_today() -> list[dict[str, Any]]:
    """Return Codex threads whose lifetime overlaps today or whose rollout changed today."""
    sqlite_path = HOME / ".codex" / "state_5.sqlite"
    threads: dict[str, dict[str, Any]] = {}

    if sqlite_path.exists():
        try:
            conn = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, source, model_provider, model, reasoning_effort, cwd,
                       tokens_used, created_at, updated_at, rollout_path
                FROM threads
                WHERE model_provider = 'openai'
                  AND updated_at >= ?
                  AND created_at < ?
                ORDER BY updated_at DESC
                """,
                (TODAY_EPOCH_START, TODAY_EPOCH_END),
            )
            for row in cur.fetchall():
                item = dict(row)
                if item.get("rollout_path"):
                    threads[item["rollout_path"]] = item
            conn.close()
        except sqlite3.Error:
            pass

    # Fallback for rollouts not yet indexed in state_5.sqlite.
    sessions_root = HOME / ".codex" / "sessions"
    if sessions_root.exists():
        for path in sessions_root.rglob("rollout-*.jsonl"):
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            if TODAY_EPOCH_START <= int(mtime) < TODAY_EPOCH_END:
                threads.setdefault(
                    str(path),
                    {
                        "id": path.stem.split("-")[-1],
                        "source": "rollout",
                        "model_provider": "openai",
                        "model": "",
                        "reasoning_effort": "",
                        "cwd": "",
                        "tokens_used": 0,
                        "created_at": 0,
                        "updated_at": int(mtime),
                        "rollout_path": str(path),
                    },
                )

    return list(threads.values())


def codex_total() -> dict[str, Any]:
    """Aggregate today's Codex usage from authoritative rollout token_count events."""
    by_model: dict[str, dict[str, int]] = {}
    thread_summaries: list[dict[str, Any]] = []

    for thread in load_codex_threads_touched_today():
        rollout_path = Path(thread.get("rollout_path") or "")
        parsed = parse_codex_rollout(rollout_path)
        if not parsed:
            continue
        model = normalize_openai_model(thread.get("model") or "")
        delta = parsed["delta_today"]
        bucket = by_model.setdefault(
            model,
            {
                "input": 0,
                "output": 0,
                "cache_read": 0,
                "uncached_input": 0,
                "reasoning": 0,
                "total": 0,
                "messages": 0,
                "threads": 0,
            },
        )
        bucket["input"] += delta["input_tokens"]
        bucket["output"] += delta["output_tokens"]
        bucket["cache_read"] += delta["cached_input_tokens"]
        bucket["uncached_input"] += max(0, delta["input_tokens"] - delta["cached_input_tokens"])
        bucket["reasoning"] += delta["reasoning_output_tokens"]
        bucket["total"] += delta["total_tokens"]
        bucket["messages"] += parsed["calls_today"]
        bucket["threads"] += 1
        thread_summaries.append(
            {
                "thread_id": thread.get("id"),
                "model": model,
                "reasoning_effort": thread.get("reasoning_effort") or "",
                "cwd": thread.get("cwd") or "",
                "rollout_path": str(rollout_path),
                "calls_today": parsed["calls_today"],
                "first_today_ts": parsed["first_today_ts"],
                "latest_today_ts": parsed["latest_today_ts"],
                "state_tokens_used": int(thread.get("tokens_used", 0) or 0),
                "today": delta,
                "latest_thread_total": parsed["latest_thread_total"],
            }
        )

    cost = 0.0
    for model, b in by_model.items():
        p = OPENAI_PRICING.get(model, OPENAI_PRICING["gpt-5.2"])
        uncached = max(0, b["input"] - b["cache_read"])
        cost += max(0, uncached) * p["in"] / 1e6
        cost += b["cache_read"] * p["cache_read"] / 1e6
        cost += b["output"] * p["out"] / 1e6

    return {
        "completions": sum(b["messages"] for b in by_model.values()),
        "by_model": by_model,
        "cost_usd": cost,
        "distinct_processes_today": len(thread_summaries),
        "threads": thread_summaries,
        "basis": "Codex rollout event_msg/token_count cumulative counters, delta since local midnight",
    }


def write_manual_entries(claude: dict[str, Any], codex: dict[str, Any]) -> None:
    """Rewrite manual-entries.jsonl: strip ALL claude/codex entries, replace with poll-derived totals.

    The poller owns claude+codex accounting end-to-end. Other providers stay.
    Also clears the claude/codex buckets in .state.json so tracker.py rebuilds them fresh.
    """
    manual_path = TRACKER_DIR / "manual-entries.jsonl"
    state_path = TRACKER_DIR / ".state.json"

    if manual_path.exists():
        keep: list[str] = []
        for l in manual_path.read_text().splitlines():
            if l.startswith("#") or not l.strip():
                keep.append(l)
                continue
            try:
                obj = json.loads(l)
            except json.JSONDecodeError:
                keep.append(l)
                continue
            if obj.get("provider") in {"claude", "codex"}:
                continue
            keep.append(l)
    else:
        keep = []

    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            state = {}
        totals = state.get("totals_by_model", {})
        for k in list(totals.keys()):
            if k.startswith("claude") or k.startswith("gpt-5") or k == "codex":
                del totals[k]
        state["totals_by_model"] = totals
        state["openrouter_calls_seen"] = [
            s for s in state.get("openrouter_calls_seen", []) if not s.startswith("manual:")
        ]
        state_path.write_text(json.dumps(state, indent=2))

    new_lines: list[str] = []
    now = dt.datetime.now().astimezone().replace(microsecond=0).isoformat()

    for model, b in claude["by_model"].items():
        p = CLAUDE_PRICING.get(model, CLAUDE_PRICING["claude-opus-4-7"])
        cost = (
            b["input"] * p["in"]
            + b["output"] * p["out"]
            + b["cache_create_5m"] * p["cache_5m"]
            + b["cache_create_1h"] * p["cache_1h"]
            + b["cache_read"] * p["cache_read"]
        ) / 1e6
        entry = {
            "ts": now,
            "POLL_GENERATED": True,
            "provider": "claude",
            "model": model,
            "tokens_in": b["input"] + b["cache_create_5m"] + b["cache_create_1h"] + b["cache_read"],
            "tokens_out": b["output"],
            "cache_read_tokens": b["cache_read"],
            "uncached_input_tokens": b["input"] + b["cache_create_5m"] + b["cache_create_1h"],
            "calls": b["messages"],
            "cost_usd": round(cost, 6),
            "purpose": "Claude Code sessions today (parsed from ~/.claude/projects/*/*.jsonl)",
            "destination_country": "US",
            "subscription_paid": True,
        }
        new_lines.append(json.dumps(entry))

    for model, b in codex["by_model"].items():
        p = OPENAI_PRICING.get(model, OPENAI_PRICING["gpt-5.2"])
        uncached = max(0, b["input"] - b["cache_read"])
        cost = (uncached * p["in"] + b["cache_read"] * p["cache_read"] + b["output"] * p["out"]) / 1e6
        entry = {
            "ts": now,
            "POLL_GENERATED": True,
            "provider": "codex",
            "model": model,
            "tokens_in": b["input"],
            "tokens_out": b["output"],
            "cache_read_tokens": b["cache_read"],
            "uncached_input_tokens": b.get("uncached_input", max(0, b["input"] - b["cache_read"])),
            "reasoning_tokens": b.get("reasoning", 0),
            "calls": b["messages"],
            "threads": b.get("threads", 0),
            "cost_usd": round(cost, 6),
            "purpose": "Codex CLI sessions today (parsed from ~/.codex/sessions rollout token_count counters)",
            "destination_country": "US",
            "subscription_paid": True,
        }
        new_lines.append(json.dumps(entry))

    manual_path.write_text("\n".join(keep + new_lines) + "\n")


def main() -> int:
    claude = claude_total()
    codex = codex_total()
    openrouter = poll_openrouter()

    summary = {"date": TODAY, "claude": claude, "codex": codex, "openrouter": openrouter}
    (TRACKER_DIR / ".real-usage.json").write_text(json.dumps(summary, indent=2, default=str))

    write_manual_entries(claude, codex)

    # Replace tracker.py's aider-grep reconstruction with OpenRouter's authoritative figure.
    # Write a marker file the main tracker can read.
    if "usage_today_usd" in openrouter:
        (TRACKER_DIR / ".openrouter-today.json").write_text(json.dumps(openrouter, indent=2))

    print(f"[poll {TODAY}]")
    print(f"  Claude sessions parsed: {len(claude['sessions'])}")
    for model, b in claude["by_model"].items():
        total_in = b["input"] + b["cache_create_5m"] + b["cache_create_1h"] + b["cache_read"]
        print(f"    {model}: {b['messages']:,} msgs, {total_in:,} in (cache_read {b['cache_read']:,}), {b['output']:,} out")
    print(f"  Claude actual cost today: ${claude['cost_usd']:.4f}")
    print(f"  Codex model calls parsed: {codex['completions']} (threads today: {codex.get('distinct_processes_today', 0)})")
    for model, b in codex["by_model"].items():
        print(f"    {model}: {b['messages']:,} calls, {b['input']:,} in (cached {b['cache_read']:,}; uncached {b.get('uncached_input', 0):,}), {b['output']:,} out (reasoning {b.get('reasoning', 0):,})")
    print(f"  Codex actual cost today: ${codex['cost_usd']:.4f}  [from rollout token_count counters]")
    print(f"  OpenRouter authoritative today: ${openrouter.get('usage_today_usd', 0):.4f} (from /auth/key)")
    combined = claude["cost_usd"] + codex["cost_usd"] + openrouter.get("usage_today_usd", 0)
    print(f"  COMBINED ACTUAL today: ${combined:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
