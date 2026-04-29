from __future__ import annotations

import math
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from . import judge_app, paths
from .challenge_contract import CHALLENGES
from .challenge_containers import build_audit_summary, build_challenges, finding_summary, all_findings
from .jsonio import read_json, write_json
from .util import now_iso, sha256_file


def public_dir(*parts: str) -> Path:
    return paths.site_public_dir().joinpath(*parts)


def _copy(src: Path, dst: Path) -> bool:
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=paths.root(),
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "uncommitted"


def as_number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def compact_number(value: float, *, digits: int = 1) -> str:
    abs_value = abs(value)
    for suffix, divisor in [("B", 1_000_000_000), ("M", 1_000_000), ("K", 1_000)]:
        if abs_value >= divisor:
            rendered = value / divisor
            text = f"{rendered:.{digits}f}".rstrip("0").rstrip(".")
            return f"{text}{suffix}"
    if value == int(value):
        return f"{int(value):,}"
    return f"{value:,.2f}"


def cad(value: Any) -> str:
    number = as_number(value)
    if number is None:
        return "not reported"
    return f"${compact_number(number)}"


def pct(value: Any) -> str:
    number = as_number(value)
    if number is None:
        return "not reported"
    if abs(number) <= 1:
        number *= 100
    return f"{number:.1f}%"


def plain_metric(value: Any, suffix: str = "") -> str:
    number = as_number(value)
    if number is None:
        return str(value) if value not in (None, "") else "not reported"
    return f"{compact_number(number)}{suffix}"


def is_currency_key(key: str) -> bool:
    key = key.lower()
    return any(part in key for part in ["amount", "amt", "spend", "fund", "govt", "grant", "value", "revenue", "cost", "severity"])


def display_metric(key: str, value: Any) -> str:
    key_l = key.lower()
    if "share" in key_l or "percent" in key_l or key_l.endswith("_pct"):
        return pct(value)
    if is_currency_key(key_l):
        return cad(value)
    if "count" in key_l or "loops" in key_l or "years" in key_l:
        return plain_metric(value)
    return plain_metric(value)


def sanitize(value: Any) -> Any:
    if value is None:
        return "not reported"
    if isinstance(value, list):
        return [sanitize(item) for item in value]
    if isinstance(value, dict):
        return {key: sanitize(item) for key, item in value.items()}
    return value


def artifact(path: Path, kind: str) -> dict[str, Any]:
    exists = path.exists()
    rel = str(path.relative_to(paths.site_public_dir())) if exists else str(path)
    return {
        "id": rel.replace("/", ":").replace(".", ":"),
        "kind": kind,
        "path": rel,
        "exists": exists,
        "bytes": path.stat().st_size if exists else 0,
        "sha256": sha256_file(path) if exists and path.is_file() else None,
    }


def copy_briefs() -> list[dict[str, Any]]:
    artifacts = []
    for loop in sorted(paths.loop_audit_dir().glob("[0-9][0-9]-*")):
        if not loop.is_dir():
            continue
        src = loop / "research-brief.md"
        dst = public_dir("briefs", f"{loop.name}.md")
        _copy(src, dst)
        artifacts.append(artifact(dst, "research_brief"))
    return artifacts


def copy_embeds() -> list[dict[str, Any]]:
    artifacts = []
    for name in ["dashboard.html", "sovereignty.html", "agency-loop-audit.html"]:
        src = paths.web_dir() / name
        dst = public_dir("embeds", name)
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            text = src.read_text(errors="replace")
            text = text.replace(": null", ': "not reported"')
            dst.write_text(text)
        artifacts.append(artifact(dst, "embed"))
    return artifacts


def build_findings_index(limit: int = 80) -> dict[str, Any]:
    findings = [finding_summary(finding) for finding in all_findings()]
    findings.sort(
        key=lambda item: (
            {"high": 3, "medium": 2, "low": 1}.get(str(item.get("severity")), 0),
            float(item.get("confidence") or 0),
        ),
        reverse=True,
    )
    by_challenge = Counter(str(item.get("challenge")) for item in findings)
    return {
        "generated_at": now_iso(),
        "total_findings": len(findings),
        "included_findings": min(limit, len(findings)),
        "by_challenge": dict(by_challenge),
        "findings": findings[:limit],
    }


def frontend_findings_index(findings_index: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for finding in findings_index.get("findings", []):
        finding_challenge = finding.get("challenge")
        challenge_number = challenge_number_for_finding(finding_challenge)
        route_id = frontend_route_id(challenge_number, finding_challenge)
        metrics = (finding.get("evidence") or {}).get("metrics") or {}
        label, value = best_metric(metrics, challenge_id=challenge_number, challenge_slug=finding_challenge)
        out.append(
            {
                "finding_id": finding.get("finding_id") or "finding",
                "challenge_id": route_id,
                "entity": finding.get("entity") or "cohort",
                "headline": finding.get("claim") or finding.get("story_type") or "Review lead",
                "top_metric": {"label": label, "value": value},
                "severity": finding.get("severity") or "medium",
                "support_status": finding.get("support_status") or finding.get("status") or "not_checked",
                "sha": (finding.get("evidence") or {}).get("sql_hash") or finding.get("finding_id") or "",
                "source_tables": [
                    table.strip()
                    for table in str((finding.get("evidence") or {}).get("table") or "").split("+")
                    if table.strip()
                ],
            }
        )
    return out


def challenge_number_for_finding(finding_challenge: Any) -> int | None:
    finding_challenge = str(finding_challenge or "")
    for challenge in CHALLENGES:
        if finding_challenge in challenge.finding_challenges:
            return challenge.id
    return None


def frontend_route_id(challenge_number: int | None, finding_challenge: Any) -> str:
    if challenge_number == 8:
        return "08a-duplicative-overlap"
    if challenge_number:
        challenge = next(item for item in CHALLENGES if item.id == challenge_number)
        return frontend_slug(challenge.id, challenge.slug)
    return str(finding_challenge or "unknown")


def build_overview(challenges: dict[str, Any], findings_index: dict[str, Any]) -> dict[str, Any]:
    schema = read_json(paths.state_dir() / "discovered.schema.json", [])
    row_total = sum(int(row.get("row_count") or 0) for row in schema)
    execution = read_json(paths.findings_dir() / "execution-proof.json", {})
    sovereignty = read_json(paths.root() / "sovereignty-tracker" / ".real-usage.json", {})
    cards = challenges.get("cards", [])
    dollars_today = sum(
        value or 0
        for value in [
            sovereignty.get("claude", {}).get("cost_usd"),
            sovereignty.get("codex", {}).get("cost_usd"),
            sovereignty.get("openrouter", {}).get("usage_today_usd"),
        ]
    )

    # Per-provider token totals (input + output + cache).
    def _sum_tokens(by_model: dict) -> int:
        total = 0
        for stats in (by_model or {}).values():
            for k in ("input", "output", "cache_create_5m", "cache_create_1h", "cache_read", "uncached_input"):
                total += int(stats.get(k) or 0)
        return total

    def _sum_msgs(by_model: dict) -> int:
        return sum(int((stats or {}).get("messages") or 0) for stats in (by_model or {}).values())

    claude_by_model = sovereignty.get("claude", {}).get("by_model", {}) or {}
    codex_by_model = sovereignty.get("codex", {}).get("by_model", {}) or {}
    claude_tokens = _sum_tokens(claude_by_model)
    codex_tokens = _sum_tokens(codex_by_model)
    claude_msgs = _sum_msgs(claude_by_model)
    codex_msgs = _sum_msgs(codex_by_model)
    proof_counts = challenges.get("proof_level_counts", {})
    status_counts = challenges.get("status_counts", {})
    return {
        "generated_at": now_iso(),
        "title": "Agency 2026 Judge Workbench",
        "source_of_truth": "GovAlta Postgres replica for direct probes; DuckDB for cached replay; Neotoma for audit memory.",
        "position": [
            "The system separates what ran from what only passed schema review.",
            "Every challenge gets a card, a roadblock list, and a next decision.",
            "Judges can explore the evidence without treating the model as the source of truth.",
        ],
        "headline_numbers": {
            "rows_scanned": row_total,
            "findings": findings_index.get("total_findings", 0),
            "dollars_today": dollars_today,
            "models_used": 3,
        },
        "status_breakdown": {
            "sql_executed": sum(count for level, count in proof_counts.items() if "sql-executed" in level),
            "schema_safe": len(cards),
            "materialized": status_counts.get("RUNNABLE_WITH_EXTRA_MATERIALIZATION", 0),
            "external_needed": status_counts.get("NEEDS_EXTERNAL_DATA", 0),
        },
        "build_meta": {
            "generated_at": now_iso(),
            "build_sha": git_sha(),
            "challenges_total": 11,
        },
        "counts": {
            "challenges": len(cards),
            "schema_tables_profiled": len(schema),
            "profiled_rows": row_total,
            "findings": findings_index.get("total_findings", 0),
            "execution_proofs": len(execution.get("proofs", [])),
            "execution_ok": sum(1 for proof in execution.get("proofs", []) if proof.get("result", {}).get("ok")),
        },
        "status_counts": challenges.get("status_counts", {}),
        "proof_level_counts": challenges.get("proof_level_counts", {}),
        "sovereignty": {
            "date": sovereignty.get("date"),
            "claude_cost_usd": sovereignty.get("claude", {}).get("cost_usd"),
            "codex_cost_usd": sovereignty.get("codex", {}).get("cost_usd"),
            "openrouter_cost_usd": sovereignty.get("openrouter", {}).get("usage_today_usd"),
            "claude_tokens_today": claude_tokens,
            "codex_tokens_today": codex_tokens,
            "claude_msgs_today": claude_msgs,
            "codex_msgs_today": codex_msgs,
        },
        "recommended_headline": (
            "Ten accountability checks. Direct queries where the data supports them. Missing evidence named instead of hidden."
        ),
    }


def frontend_status(card: dict[str, Any]) -> str:
    if card.get("challenge_id") == 8 and card.get("_split") == "overlap":
        return "materialized"
    status = card.get("status")
    if status == "RUNNABLE_NOW":
        return "runnable"
    if status == "RUNNABLE_WITH_EXTRA_MATERIALIZATION":
        return "materialized"
    if status == "NEEDS_EXTERNAL_DATA":
        return "external"
    return "refused"


def frontend_proof_levels(card: dict[str, Any]) -> list[str]:
    levels = ["schema-safe"]
    proof = str(card.get("proof_level") or "")
    if "sql-executed" in proof:
        levels.append("sql-executed")
    if card.get("status") == "RUNNABLE_WITH_EXTRA_MATERIALIZATION" or "partial" in proof:
        levels.append("materialized")
    if card.get("status") == "NEEDS_EXTERNAL_DATA" or "external" in proof:
        levels.append("external-needed")
    return list(dict.fromkeys(levels))


def frontend_id(number: int, suffix: str | None = None) -> str:
    return f"{number:02d}{suffix or ''}"


def frontend_slug(number: int, slug: str, suffix: str | None = None) -> str:
    if number == 8 and suffix == "a":
        return "08a-duplicative-overlap"
    if number == 8 and suffix == "b":
        return "08b-funding-gaps"
    return f"{number:02d}-{slug}"


def best_metric(metrics: dict[str, Any], *, challenge_id: int | None = None, challenge_slug: str | None = None) -> tuple[str, str]:
    challenge_slug = str(challenge_slug or "")
    if challenge_id == 4 or "amendment" in challenge_slug:
        original = metrics.get("original_value")
        current = metrics.get("current_value")
        multiple = metrics.get("multiple")
        if original is not None and current is not None:
            tail = f" ({plain_metric(multiple, 'x')})" if multiple is not None else ""
            return "original to current", f"{cad(original)} -> {cad(current)}{tail}"

    if challenge_id == 8 or "tri_jurisdictional" in challenge_slug:
        fed = as_number(metrics.get("fed_total") or metrics.get("fed_total_grants"))
        ab = as_number(metrics.get("ab_total") or metrics.get("ab_total_grants"))
        if fed is not None or ab is not None:
            return "combined funding", cad((fed or 0) + (ab or 0))

    ordered = {
        1: ["total_govt_reported", "total_govt"],
        2: ["total_govt", "avg_gov_share", "years_seen"],
        3: ["total_circular_amt", "total_loops"],
        5: ["vendor_spend", "ministry_spend", "top_share"],
        6: ["bn_count"],
        7: ["agreement_value"],
        9: ["spend", "avg_contract_value"],
        10: ["severity"],
    }.get(challenge_id, [])

    for key in ordered:
        if metrics.get(key) is not None:
            label = key.replace("_", " ")
            value = display_metric(key, metrics[key])
            if key == "bn_count":
                value = f"{plain_metric(metrics[key])} charity BNs"
            if challenge_id == 10 and key == "severity":
                label = "internal mismatch"
            return label, value

    for key, value in metrics.items():
        if isinstance(value, (int, float)) or as_number(value) is not None:
            return key.replace("_", " "), display_metric(key, value)
    return "signal", "review lead"


def frontend_hero(card: dict[str, Any], *, suffix: str | None = None) -> dict[str, Any]:
    if suffix == "b":
        return {
            "entity": "Policy-priority corpus required",
            "metric": {"label": "external data needed", "value": "policy commitments"},
            "bullets": [
                "This check cannot be completed from the supplied database alone.",
                "The next source needed is a policy-priority list, then funding can be compared against it.",
                "No finding is promoted until that outside source is attached.",
            ],
            "pattern": card.get("ai_native_pattern"),
        }

    hero = card.get("hero_finding") or {}
    metrics = (hero.get("evidence") or {}).get("metrics") or {}
    metric_label, metric_value = best_metric(metrics, challenge_id=card.get("challenge_id"), challenge_slug=hero.get("challenge"))
    return {
        "entity": hero.get("entity") or "cohort",
        "metric": {"label": metric_label, "value": metric_value},
        "bullets": [
            hero.get("claim") or card.get("presentation_sentence"),
            proof_sentence(card),
            source_sentence(card),
        ],
        "pattern": card.get("ai_native_pattern"),
    }


def proof_sentence(card: dict[str, Any]) -> str:
    proof = str(card.get("proof_level") or "")
    if "external-needed" in proof or "external" in proof:
        return "Evidence status: the source-data query ran, but the final claim needs an outside source."
    if "partial" in proof or card.get("status") == "RUNNABLE_WITH_EXTRA_MATERIALIZATION":
        return "Evidence status: the source-data query ran, with one prepared dataset or follow-up source still needed."
    if "sql-executed" in proof:
        return "Evidence status: the source-data query ran and produced a review list."
    return "Evidence status: data fields were verified, but this check has not been promoted."


def source_sentence(card: dict[str, Any]) -> str:
    tables = card.get("tables_joined", {}).get("tables", [])
    if not tables:
        return "Source data: not reported."
    visible = ", ".join(tables[:3])
    more = f" and {len(tables) - 3} more" if len(tables) > 3 else ""
    return f"Source data: {visible}{more}."


def frontend_card(card: dict[str, Any], *, suffix: str | None = None, title_suffix: str | None = None) -> dict[str, Any]:
    number = int(card["challenge_id"])
    clone = dict(card)
    if suffix == "a":
        clone["_split"] = "overlap"
        clone["status"] = "RUNNABLE_WITH_EXTRA_MATERIALIZATION"
        clone["roadblocks"] = [
            "Overlap is executable from golden records.",
            "Same-purpose duplication needs purpose, period, and eligible-cost comparison.",
        ]
    if suffix == "b":
        clone["_split"] = "gaps"
        clone["status"] = "NEEDS_EXTERNAL_DATA"
        clone["roadblocks"] = [
            "Funding gaps need a policy-priority corpus.",
            "The database can show zero funding only after the priority universe is defined.",
        ]
        clone["hero_finding"] = None
    proof = clone.get("execution_proof") or {}
    tables = clone.get("tables_joined", {}).get("tables", [])
    sql_hash = proof.get("sql_hash")
    return {
        "id": frontend_id(number, suffix),
        "number": number,
        "challenge_id": number,
        "slug": frontend_slug(number, card["slug"], suffix),
        "title": card["name"] + (f" {title_suffix}" if title_suffix else ""),
        "subtitle": card.get("ai_native_pattern"),
        "brief_excerpt": card.get("challenge_statement"),
        "presentation_sentence": clone.get("presentation_sentence"),
        "status": frontend_status(clone),
        "proof_levels": frontend_proof_levels(clone),
        "hero_finding": frontend_hero(clone, suffix=suffix),
        "roadblocks": clone.get("roadblocks", []),
        "tables_joined": tables,
        "execution_status": {
            "ran": bool(proof.get("ok")),
            "row_count": len(proof.get("result_preview") or []),
            "runtime_ms": proof.get("elapsed_ms"),
            "sql_hash": sql_hash,
            "label": clone.get("execution_status"),
        },
        "replay_sql": (read_json(paths.findings_dir() / "execution-proof.json", {}).get("proofs", [{}]) or [{}])[
            max(0, number - 1)
        ].get("result", {}).get("sql"),
        "disconfirm_check": (clone.get("roadblocks") or ["Run the countercheck before promoting."])[0],
        "decision_prompt": clone.get("decision_prompt"),
        "related_findings": [],
        "brief_path": f"/briefs/{card['brief']['public_path'].split('/')[-1]}",
        "claim_safety": clone.get("claim_safety"),
    }


def build_frontend_challenges(challenges: dict[str, Any]) -> list[dict[str, Any]]:
    cards = []
    for card in challenges.get("cards", []):
        if card["challenge_id"] == 8:
            cards.append(frontend_card(card, suffix="a", title_suffix="Overlap"))
            cards.append(frontend_card(card, suffix="b", title_suffix="Gaps"))
        else:
            cards.append(frontend_card(card))
    return cards


def build_frontend_execution_proof() -> list[dict[str, Any]]:
    raw = read_json(paths.findings_dir() / "execution-proof.json", {})
    out = []
    for proof in raw.get("proofs", []):
        challenge_id = int(proof["challenge_id"])
        ids = [frontend_id(challenge_id)]
        if challenge_id == 8:
            ids = ["08a", "08b"]
        for item_id in ids:
            result = proof.get("result") or {}
            out.append(
                {
                    "challenge_id": item_id,
                    "number": challenge_id,
                    "probe": proof.get("probe"),
                    "proof_level": proof.get("proof_level"),
                    "status": proof.get("status"),
                    "probe_sql": result.get("sql"),
                    "sql_hash": result.get("sql_hash"),
                    "ran_at": raw.get("generated_at"),
                    "runtime_ms": result.get("elapsed_ms"),
                    "row_count": result.get("rows_returned"),
                    "tables_touched": proof.get("tables_joined", {}).get("tables", []),
                    "result_preview": sanitize(result.get("rows", [])[:5]),
                    "missing": {
                        "tables": [],
                        "fields": [],
                        "external_sources": proof.get("missing", []),
                    },
                }
            )
    return out


def build_qa_context(challenges: dict[str, Any], audit_summary: dict[str, Any], findings_index: dict[str, Any]) -> dict[str, Any]:
    schema = read_json(paths.state_dir() / "discovered.schema.json", [])
    schema_summary = [
        {
            "table": row.get("table"),
            "row_count": row.get("row_count"),
            "columns": [col.get("name") for col in row.get("columns", [])],
        }
        for row in schema
    ]
    review = read_json(paths.state_dir() / "review.json", {})
    return {
        "generated_at": now_iso(),
        "system_rules": [
            "Answer only from the supplied evidence bundle.",
            "Cite challenge ID, finding ID, SQL hash, or audit SHA for factual claims.",
            "Use review lead language unless the proof level supports more.",
            "Do not use em dashes.",
            "Refuse claims past the data.",
        ],
        "schema_summary": schema_summary,
        "challenges": challenges.get("cards", []),
        "audit_summary": audit_summary,
        "top_findings": findings_index.get("findings", [])[:30],
        "review_stories": review.get("stories", [])[:60],
    }


def frontend_audit_summary(audit_summary: dict[str, Any]) -> dict[str, Any]:
    per = []
    for idx, card in enumerate(audit_summary.get("cards", []), start=1):
        verdict = "clean" if card.get("sha256") else "missing"
        ids = [frontend_id(idx)]
        if idx == 8:
            ids = ["08a", "08b"]
        for item_id in ids:
            per.append(
                {
                    "id": item_id,
                    "number": idx,
                    "verdict": verdict,
                    "sha256": card.get("sha256"),
                    "sql_blocks": card.get("sql_block_count", 0),
                    "status": card.get("current_executable_status"),
                    "presentation_sentence": card.get("presentation_sentence"),
                }
            )
    return {
        "generated_at": audit_summary.get("generated_at"),
        "total": len(per),
        "clean": sum(1 for item in per if item["verdict"] == "clean"),
        "needs_review": 0,
        "unsafe": 0,
        "per_challenge": per,
        "note": audit_summary.get("note"),
    }


def build_hhi_chart(challenges: dict[str, Any]) -> dict[str, Any]:
    card = next((row for row in challenges.get("cards", []) if row.get("challenge_id") == 5), {})
    rows = card.get("execution_proof", {}).get("result_preview", [])
    def hhi_scale(value: Any) -> int:
        number = as_number(value) or 0
        if number <= 1:
            number *= 10000
        return round(number)

    return {
        "generated_at": now_iso(),
        "type": "horizontal_bar",
        "title": "Alberta sole-source ministry HHI",
        "caption": "Top Alberta ministries by HHI in the sole-source dataset.",
        "labels": [row.get("ministry") for row in rows],
        "data": [
            {
                "department": row.get("ministry"),
                "hhi": hhi_scale(row.get("hhi")),
                "top_vendor": row.get("top_vendor") or "top vendor not materialized",
                "top_share": row.get("top_share"),
                "program_count": row.get("vendor_count"),
            }
            for row in rows
        ],
        "thresholds": {"competitive": 1500, "concentrated": 2500},
        "datasets": [
            {
                "label": "HHI",
                "data": [hhi_scale(row.get("hhi")) for row in rows],
            },
            {
                "label": "Top vendor share",
                "data": [row.get("top_share") for row in rows],
            },
        ],
    }


def build_sankey_chart() -> dict[str, Any]:
    data = read_json(paths.findings_dir() / "tri-jurisdictional-funding.json", {})
    findings = data.get("findings", [])[:20]
    links = []
    nodes = {"Federal": {"id": "Federal", "label": "Federal"}, "Alberta": {"id": "Alberta", "label": "Alberta"}}
    for finding in findings:
        metrics = (finding.get("evidence") or [{}])[0].get("metrics", {})
        entity = finding.get("entity")
        fed = float(metrics.get("fed_total") or 0)
        ab = float(metrics.get("ab_total") or 0)
        if entity:
            nodes[entity] = {"id": entity, "label": entity}
        if entity and fed:
            links.append({"source": "Federal", "target": entity, "value": fed, "from": "Federal", "to": entity, "flow": fed})
        if entity and ab:
            links.append({"source": entity, "target": "Alberta", "value": ab, "from": entity, "to": "Alberta", "flow": ab})
    return {
        "generated_at": now_iso(),
        "type": "sankey",
        "title": "Tri-jurisdictional funding overlap",
        "caption": "Top entities with both federal and Alberta funding, using GovAlta golden records.",
        "nodes": list(nodes.values()),
        "links": links,
    }


def build_cost_chart() -> dict[str, Any]:
    usage = read_json(paths.root() / "sovereignty-tracker" / ".real-usage.json", {})
    return {
        "generated_at": now_iso(),
        "type": "cost_over_time",
        "title": "Model usage and routing",
        "date": usage.get("date"),
        "caption": "API-equivalent cost by provider for the event day.",
        "series": [
            {
                "provider": "anthropic",
                "label": "Claude",
                "points": [{"ts": usage.get("date"), "cost_usd": usage.get("claude", {}).get("cost_usd", 0)}],
            },
            {
                "provider": "openai",
                "label": "Codex",
                "points": [{"ts": usage.get("date"), "cost_usd": usage.get("codex", {}).get("cost_usd", 0)}],
            },
            {
                "provider": "openrouter",
                "label": "OpenRouter",
                "points": [{"ts": usage.get("date"), "cost_usd": usage.get("openrouter", {}).get("usage_today_usd", 0)}],
            },
        ],
        "providers": [
            {"provider": "Claude", "cost_usd": usage.get("claude", {}).get("cost_usd", 0)},
            {"provider": "Codex", "cost_usd": usage.get("codex", {}).get("cost_usd", 0)},
            {"provider": "OpenRouter", "cost_usd": usage.get("openrouter", {}).get("usage_today_usd", 0)},
        ],
    }


def build_charts(challenges: dict[str, Any]) -> list[dict[str, Any]]:
    charts = {
        "hhi-distribution.json": build_hhi_chart(challenges),
        "hhi-by-department.json": build_hhi_chart(challenges),
        "tri-jurisdictional-sankey.json": build_sankey_chart(),
        "sovereignty-cost.json": build_cost_chart(),
        "cost-over-time.json": build_cost_chart(),
    }
    artifacts = []
    for name, data in charts.items():
        path = public_dir("charts", name)
        write_json(path, data)
        artifacts.append(artifact(path, "chart"))
        data_path = public_dir("data", "charts", name)
        write_json(data_path, data)
        artifacts.append(artifact(data_path, "chart"))
    return artifacts


def build_manifest(artifacts: list[dict[str, Any]], overview: dict[str, Any]) -> dict[str, Any]:
    return {
        "generated_at": now_iso(),
        "version": "judge-app-contract-v1",
        "overview": overview,
        "artifacts": artifacts,
        "frontend_contract": {
            "source": "site/public/data/app-manifest.json",
            "rule": "Frontend reads generated JSON. It does not scrape HTML proof artifacts.",
            "shared_runtime": str(paths.judge_app_dir().relative_to(paths.root())),
        },
    }


def public_export() -> dict[str, Any]:
    paths.ensure_dirs()
    judge_app.init_shared_runtime()

    challenges = build_challenges()
    frontend_challenges = build_frontend_challenges(challenges)
    findings_index = build_findings_index()
    frontend_findings = frontend_findings_index(findings_index)
    audit_summary = build_audit_summary()
    audit_frontend = frontend_audit_summary(audit_summary)
    overview = build_overview(challenges, findings_index)
    frontend_status_counts = Counter(card["status"] for card in frontend_challenges)
    overview["status_breakdown"] = {
        "sql_executed": sum(1 for card in frontend_challenges if "sql-executed" in card.get("proof_levels", [])),
        "schema_safe": len(frontend_challenges),
        "materialized": frontend_status_counts.get("materialized", 0),
        "external_needed": frontend_status_counts.get("external", 0),
    }
    overview["build_meta"]["challenges_total"] = len(frontend_challenges)
    qa_context = build_qa_context({"cards": frontend_challenges}, audit_frontend, findings_index)

    data_artifacts = {
        "challenges.json": frontend_challenges,
        "challenge-containers.json": sanitize(challenges),
        "findings-index.json": frontend_findings,
        "audit-summary.json": audit_frontend,
        "audit-summary-raw.json": sanitize(audit_summary),
        "overview.json": overview,
        "qa-context.json": sanitize(qa_context),
    }
    execution = read_json(paths.findings_dir() / "execution-proof.json", None)
    if execution:
        data_artifacts["execution-proof.json"] = build_frontend_execution_proof()
        data_artifacts["execution-proof-summary.json"] = sanitize(execution)

    artifacts: list[dict[str, Any]] = []
    for name, data in data_artifacts.items():
        path = public_dir("data", name)
        write_json(path, data)
        artifacts.append(artifact(path, "data"))

    artifacts.extend(copy_briefs())
    artifacts.extend(copy_embeds())
    artifacts.extend(build_charts(challenges))

    manifest = build_manifest(artifacts, overview)
    manifest_path = public_dir("data", "app-manifest.json")
    write_json(manifest_path, manifest)
    artifacts.append(artifact(manifest_path, "data"))
    manifest["artifacts"] = artifacts
    write_json(manifest_path, manifest)
    judge_app.write_manifest(manifest)
    judge_app.update_handoff(
        {
            "manifest_path": "site/public/data/app-manifest.json",
            "challenges_path": "site/public/data/challenges.json",
            "qa_context_path": "site/public/data/qa-context.json",
            "execution_proof_path": "site/public/data/execution-proof.json",
            "notes": [
                "Challenge pages should render from challenges.json first, markdown briefs second.",
                "Proof-level chips are available per challenge.",
                "The static site remains useful even if the live droplet API is offline.",
            ],
        }
    )
    judge_app.backend_event(
        "public_export_completed",
        {"artifact_count": len(artifacts), "manifest": "site/public/data/app-manifest.json"},
    )
    return {"manifest": manifest_path, "artifact_count": len(artifacts), "overview": overview}
