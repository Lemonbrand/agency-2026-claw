from __future__ import annotations

import html
import json
from typing import Any

from . import paths
from .jsonio import read_json


CHALLENGE_LABELS = {
    "amendment_creep": "Amendment creep",
    "vendor_concentration": "Vendor concentration",
    "related_parties": "Related parties",
}

STORY_TYPE_LABELS = {
    "risk": "Risk",
    "opportunity": "Opportunity",
    "capacity": "Capacity",
    "policy_gap": "Policy gap",
    "success": "Success",
    "operating_insight": "Operating insight",
}

COLUMN_DEFS = [
    {
        "key": "risks",
        "title": "Risks worth reviewing",
        "subtitle": "Stories that suggest someone should pull a file.",
        "story_types": {"risk"},
        "accent": "red",
    },
    {
        "key": "operating",
        "title": "Operating insight",
        "subtitle": "Stories that change how a system is understood, not just what to flag.",
        "story_types": {"operating_insight", "capacity", "policy_gap"},
        "accent": "gold",
    },
    {
        "key": "opportunities",
        "title": "Opportunities and success",
        "subtitle": "Stories that point to programs to scale or document.",
        "story_types": {"opportunity", "success"},
        "accent": "green",
    },
]


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def by_id(findings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("finding_id")): row for row in findings}


def column_for_story_type(story_type: str) -> str:
    for column in COLUMN_DEFS:
        if story_type in column["story_types"]:
            return column["key"]
    return "operating"


def _stories_with_evidence(stories: list[dict[str, Any]], findings_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for story in stories:
        finding = findings_by_id.get(str(story.get("finding_id")), {})
        merged = dict(story)
        merged["challenge"] = finding.get("challenge")
        merged["severity"] = finding.get("severity")
        merged["support_status"] = finding.get("support_status")
        merged["replayed"] = bool(finding.get("verification", {}).get("replayed"))
        merged["evidence"] = (finding.get("evidence") or [{}])[0]
        out.append(merged)
    return out


def render_plan_panel(plan: dict[str, Any]) -> str:
    selected = plan.get("selected", [])
    rejected = plan.get("rejected", [])
    considered = len(selected) + len(rejected)

    selected_items = "".join(
        f"<li><strong>{esc(item.get('skill'))}</strong> &mdash; {esc(item.get('reason') or '')}</li>"
        for item in selected
    )
    rejected_items = "".join(
        f"<li><strong>{esc(item.get('skill'))}</strong> &mdash; {esc(item.get('reason') or '')}</li>"
        for item in rejected
    )

    return f"""
    <section class="plan">
      <div class="plan-head">
        <div class="plan-counts">
          <div><strong>{considered}</strong><span>stories considered</span></div>
          <div><strong>{len(selected)}</strong><span>told</span></div>
          <div><strong>{len(rejected)}</strong><span>rejected with reasons</span></div>
        </div>
        <p class="plan-note">
          The agentic move is choosing what to investigate from unknown data, and refusing to investigate
          what the data does not support. Selection and rejection are both deliverables.
        </p>
      </div>
      <div class="plan-grid">
        <details open>
          <summary>Told</summary>
          <ul class="plan-list selected">{selected_items or '<li class="empty">No skills selected.</li>'}</ul>
        </details>
        <details>
          <summary>Rejected</summary>
          <ul class="plan-list rejected">{rejected_items or '<li class="empty">No skills rejected.</li>'}</ul>
        </details>
      </div>
    </section>
    """


def render_cross_signal(correlated: dict[str, Any]) -> str:
    multi = [item for item in correlated.get("entities", []) if int(item.get("challenge_count", 0)) >= 2]
    if not multi:
        return ""
    cards = []
    for item in multi[:3]:
        challenges = ", ".join(CHALLENGE_LABELS.get(ch, ch) for ch in item.get("challenges", []))
        members = item.get("members", [])
        member_text = (
            f"Includes name variants: {esc(', '.join(members))}." if len(members) > 1 else ""
        )
        cards.append(
            f"""
            <article class="cross-card">
              <div class="cross-rank">{esc(item.get('score'))}</div>
              <div>
                <h3>{esc(item.get('entity'))}</h3>
                <p>Surfaces in: {esc(challenges)}.</p>
                <p class="member-note">{member_text}</p>
              </div>
            </article>
            """
        )
    return f"""
    <section class="cross-signal">
      <h2>Cross-signal entities</h2>
      <p class="note">Entities that appear in more than one independent story. Reviewers usually start here.</p>
      <div class="cross-grid">{''.join(cards)}</div>
    </section>
    """


def render_story_card(story: dict[str, Any]) -> str:
    support_label = {
        "supported": "supported",
        "contested": "contested",
        "inconclusive": "inconclusive",
    }.get(story.get("support_status"), "not_checked")
    severity = story.get("severity") or "review"
    challenge = CHALLENGE_LABELS.get(story.get("challenge"), story.get("challenge") or "")
    evidence = story.get("evidence") or {}
    evidence_summary = story.get("evidence_summary") or evidence.get("summary", "")

    return f"""
    <article class="story-card">
      <header>
        <span class="story-type">{esc(STORY_TYPE_LABELS.get(story.get('story_type'), story.get('story_type')))}</span>
        <span class="story-lens">{esc(story.get('lens') or '')}</span>
      </header>
      <h3>{esc(story.get('what_happened'))}</h3>
      <p class="why">{esc(story.get('why_it_matters'))}</p>
      <dl>
        <dt>Who is affected</dt><dd>{esc(story.get('who_is_affected'))}</dd>
        <dt>Evidence</dt><dd>{esc(evidence_summary)}</dd>
        <dt>What could disprove this</dt><dd>{esc(story.get('what_could_disprove'))}</dd>
        <dt>What to check next</dt><dd>{esc(story.get('what_to_check_next'))}</dd>
        <dt>Decision this enables</dt><dd>{esc(story.get('decision_enabled'))}</dd>
      </dl>
      <footer>
        <span class="tag">{esc(challenge)}</span>
        <span class="tag">{esc(severity)} severity</span>
        <span class="tag support-{esc(support_label)}">{esc(support_label.replace('_', ' '))}</span>
        <span class="tag {'replayed' if story.get('replayed') else 'unreplayed'}">{'replay ok' if story.get('replayed') else 'replay missing'}</span>
      </footer>
    </article>
    """


def render_columns(stories: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = {col["key"]: [] for col in COLUMN_DEFS}
    for story in stories:
        key = column_for_story_type(story.get("story_type", ""))
        grouped[key].append(story)

    columns_html = []
    for column in COLUMN_DEFS:
        items = grouped.get(column["key"], [])
        cards = "".join(render_story_card(story) for story in items)
        if not cards:
            cards = "<p class='empty'>No stories of this type were told from the loaded data.</p>"
        columns_html.append(
            f"""
            <section class="column accent-{column['accent']}">
              <header>
                <h2>{esc(column['title'])}</h2>
                <p>{esc(column['subtitle'])}</p>
                <span class="count">{len(items)}</span>
              </header>
              <div class="cards">{cards}</div>
            </section>
            """
        )
    return f"<div class='columns'>{''.join(columns_html)}</div>"


def render_finding_register(findings: list[dict[str, Any]]) -> str:
    rows = []
    for finding in findings:
        evidence = (finding.get("evidence") or [{}])[0]
        replayed = finding.get("verification", {}).get("replayed")
        rows.append(
            "<tr>"
            f"<td>{esc(STORY_TYPE_LABELS.get(finding.get('story_type'), finding.get('story_type')))}</td>"
            f"<td>{esc(CHALLENGE_LABELS.get(finding.get('challenge'), finding.get('challenge')))}</td>"
            f"<td>{esc(finding.get('entity'))}</td>"
            f"<td>{esc(finding.get('severity'))}</td>"
            f"<td>{esc(finding.get('support_status') or 'not_checked')}</td>"
            f"<td>{'replayed' if replayed else 'not replayed'}</td>"
            f"<td>{esc(evidence.get('summary', ''))}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_sql_details(findings: list[dict[str, Any]]) -> str:
    blocks = []
    for finding in findings:
        evidence = (finding.get("evidence") or [{}])[0]
        sql = evidence.get("sql", "")
        if not sql:
            continue
        blocks.append(
            "<details class='sql-block'>"
            f"<summary>{esc(finding.get('claim'))}</summary>"
            f"<pre>{esc(sql)}</pre>"
            "</details>"
        )
    return "".join(blocks) or "<p class='note'>No replayable SQL captured yet.</p>"


def render() -> str:
    plan = read_json(paths.state_dir() / "investigation-plan.json", {"selected": [], "rejected": []})
    correlated = read_json(paths.findings_dir() / "correlated.json", {"entities": []})
    verified = read_json(paths.findings_dir() / "verified.json", {"findings": []})
    review = read_json(paths.state_dir() / "review.json", {"stories": [], "issues": [], "recommended_language": ""})
    schema = read_json(paths.state_dir() / "discovered.schema.json", [])

    findings = verified.get("findings", [])
    findings_by_id = by_id(findings)
    stories = _stories_with_evidence(review.get("stories", []), findings_by_id)
    replayed_count = sum(1 for row in findings if row.get("verification", {}).get("replayed"))
    schema_json = esc(json.dumps(schema, indent=2)[:6000])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>LemonClaw &mdash; Accountability Stories</title>
  <style>
    :root {{
      --ink: #18130c;
      --paper: #fbf7ed;
      --panel: #ffffff;
      --line: #e0d6c1;
      --muted: #6b6354;
      --gold: #c47a1d;
      --red: #993f3f;
      --green: #2c684f;
      --blue: #2a5277;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter", sans-serif; background: var(--paper); color: var(--ink); }}
    header.top {{ padding: 28px 32px 22px; background: var(--ink); color: var(--paper); }}
    header.top h1 {{ margin: 0; font-size: 32px; letter-spacing: -0.01em; font-weight: 800; }}
    header.top .tagline {{ margin: 6px 0 0; color: #f1ddb6; font-size: 15px; max-width: 920px; line-height: 1.45; }}
    main {{ padding: 24px 32px 64px; max-width: 1480px; margin: 0 auto; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 26px; line-height: 1; }}
    .metric span {{ display: block; margin-top: 6px; color: var(--muted); font-size: 13px; }}
    .plan {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 18px 20px; margin-bottom: 22px; }}
    .plan-head {{ display: grid; grid-template-columns: minmax(220px, auto) 1fr; gap: 24px; align-items: center; }}
    .plan-counts {{ display: flex; gap: 12px; flex-wrap: wrap; }}
    .plan-counts div {{ background: var(--paper); border: 1px solid var(--line); padding: 10px 14px; border-radius: 8px; }}
    .plan-counts strong {{ font-size: 22px; display: block; line-height: 1; }}
    .plan-counts span {{ color: var(--muted); font-size: 12px; }}
    .plan-note {{ margin: 0; color: var(--muted); font-size: 14px; line-height: 1.5; }}
    .plan-grid {{ margin-top: 14px; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
    .plan-grid summary {{ cursor: pointer; font-weight: 700; }}
    .plan-list {{ list-style: none; padding-left: 0; margin: 8px 0 0; }}
    .plan-list li {{ padding: 6px 0; border-bottom: 1px dashed var(--line); font-size: 14px; line-height: 1.45; }}
    .plan-list li:last-child {{ border-bottom: 0; }}
    .plan-list li.empty {{ color: var(--muted); font-style: italic; }}
    .cross-signal {{ margin-bottom: 22px; }}
    .cross-signal h2 {{ margin: 0 0 6px; font-size: 18px; }}
    .cross-signal .note {{ margin: 0 0 10px; color: var(--muted); font-size: 13px; }}
    .cross-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .cross-card {{ display: grid; grid-template-columns: 48px 1fr; gap: 12px; padding: 12px; background: var(--panel); border: 1px solid var(--line); border-left: 4px solid var(--blue); border-radius: 10px; }}
    .cross-rank {{ background: var(--blue); color: var(--paper); font-weight: 700; border-radius: 8px; display: grid; place-items: center; }}
    .cross-card h3 {{ margin: 0 0 4px; font-size: 15px; }}
    .cross-card p {{ margin: 0; color: var(--muted); font-size: 13px; line-height: 1.45; }}
    .cross-card .member-note {{ font-style: italic; }}
    .columns {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 28px; }}
    .column {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }}
    .column.accent-red {{ border-top: 4px solid var(--red); }}
    .column.accent-gold {{ border-top: 4px solid var(--gold); }}
    .column.accent-green {{ border-top: 4px solid var(--green); }}
    .column header {{ padding: 14px 16px 10px; border-bottom: 1px solid var(--line); display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 6px; }}
    .column header h2 {{ margin: 0; font-size: 17px; }}
    .column header p {{ margin: 4px 0 0; color: var(--muted); font-size: 13px; line-height: 1.4; grid-column: 1 / span 2; }}
    .column header .count {{ color: var(--muted); font-size: 13px; }}
    .column .cards {{ padding: 14px; display: grid; gap: 12px; }}
    .column .empty {{ color: var(--muted); font-size: 13px; font-style: italic; padding: 18px 0; text-align: center; }}
    .story-card {{ background: var(--paper); border: 1px solid var(--line); border-radius: 10px; padding: 14px; }}
    .story-card header {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 6px; padding: 0; border: 0; background: transparent; color: inherit; }}
    .story-card .story-type {{ font-size: 11px; font-weight: 800; letter-spacing: 0.05em; text-transform: uppercase; padding: 3px 8px; border-radius: 999px; background: var(--ink); color: var(--paper); }}
    .story-card .story-lens {{ font-size: 12px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .story-card h3 {{ margin: 4px 0 6px; font-size: 16px; line-height: 1.3; }}
    .story-card .why {{ margin: 0 0 10px; color: var(--muted); font-size: 13px; line-height: 1.5; }}
    .story-card dl {{ margin: 0; display: grid; grid-template-columns: 1fr; gap: 6px; }}
    .story-card dt {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--blue); font-weight: 700; }}
    .story-card dd {{ margin: 0 0 6px; font-size: 13px; line-height: 1.5; }}
    .story-card footer {{ margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; padding: 0; border: 0; background: transparent; color: inherit; }}
    .tag {{ font-size: 11px; padding: 3px 8px; border-radius: 999px; background: #efe6cf; color: var(--ink); }}
    .tag.support-supported {{ background: #d6e9d8; color: var(--green); }}
    .tag.support-contested {{ background: #f1d6d6; color: var(--red); }}
    .tag.support-inconclusive {{ background: #efe6cf; color: var(--gold); }}
    .tag.support-not_checked {{ background: #e7e2d4; color: var(--muted); }}
    .tag.replayed {{ background: #d6e9d8; color: var(--green); }}
    .tag.unreplayed {{ background: #f1d6d6; color: var(--red); }}
    h2.section {{ margin: 28px 0 10px; font-size: 17px; }}
    .audit {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 16px 18px; }}
    .audit summary {{ cursor: pointer; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); font-size: 13px; vertical-align: top; }}
    th {{ background: var(--paper); color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; }}
    .sql-block {{ margin-top: 8px; }}
    .sql-block summary {{ font-weight: 600; color: var(--gold); }}
    pre {{ max-height: 280px; overflow: auto; background: #1a160d; color: #f5e9c8; padding: 12px; border-radius: 8px; font-size: 12px; line-height: 1.45; }}
    .note {{ color: var(--muted); font-size: 13px; line-height: 1.5; max-width: 920px; margin: 0; }}
    @media (max-width: 1100px) {{
      .columns {{ grid-template-columns: 1fr; }}
      .cross-grid {{ grid-template-columns: 1fr; }}
      .summary {{ grid-template-columns: 1fr 1fr; }}
      .plan-head {{ grid-template-columns: 1fr; }}
      .plan-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header class="top">
    <h1>LemonClaw</h1>
    <p class="tagline">An accountability story engine. The agent looks at unknown public-sector data, decides what stories the data can tell, tells them with evidence and caveats, and refuses the rest with reasons.</p>
  </header>
  <main>
    <section class="summary">
      <div class="metric"><strong>{len(plan.get('selected', [])) + len(plan.get('rejected', []))}</strong><span>stories considered</span></div>
      <div class="metric"><strong>{len(stories)}</strong><span>stories told</span></div>
      <div class="metric"><strong>{replayed_count}/{len(findings)}</strong><span>findings replayed</span></div>
      <div class="metric"><strong>{len(schema)}</strong><span>tables loaded</span></div>
    </section>

    {render_plan_panel(plan)}

    {render_cross_signal(correlated)}

    {render_columns(stories)}

    <h2 class="section">Audit trail</h2>
    <details class="audit">
      <summary>Finding register</summary>
      <p class="note">Every story above has a row here. Every row should be traceable back to a source file and a saved SQL query.</p>
      <table>
        <thead><tr><th>Story</th><th>Skill</th><th>Subject</th><th>Severity</th><th>Support</th><th>Replay</th><th>Summary</th></tr></thead>
        <tbody>{render_finding_register(findings)}</tbody>
      </table>
    </details>
    <details class="audit" style="margin-top: 12px;">
      <summary>SQL replay pack</summary>
      <p class="note">Open these only when someone asks how a story was produced. The pitch should stay on the columns above.</p>
      {render_sql_details(findings)}
    </details>
    <details class="audit" style="margin-top: 12px;">
      <summary>Loaded data shape</summary>
      <pre>{schema_json}</pre>
    </details>
  </main>
</body>
</html>
"""


def write_dashboard() -> str:
    paths.ensure_dirs()
    out = paths.web_dir() / "dashboard.html"
    out.write_text(render())
    return str(out)
