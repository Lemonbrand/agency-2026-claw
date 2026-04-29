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


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else ""))


def pct(value: Any) -> str:
    try:
        return "{:.1%}".format(float(value))
    except (TypeError, ValueError):
        return "unknown"


def multiple(value: Any) -> str:
    try:
        return "{:.1f}x".format(float(value))
    except (TypeError, ValueError):
        return "unknown multiple"


def by_id(findings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("finding_id")): row for row in findings}


def first_metric(findings: list[dict[str, Any]], challenge: str, key: str) -> Any:
    for finding in findings:
        if finding.get("challenge") != challenge:
            continue
        evidence = (finding.get("evidence") or [{}])[0]
        metrics = evidence.get("metrics") or {}
        if key in metrics:
            return metrics[key]
    return None


def proof_line(finding: dict[str, Any]) -> str:
    evidence = (finding.get("evidence") or [{}])[0]
    table = evidence.get("table", "unknown table")
    replayed = finding.get("verification", {}).get("replayed")
    status = "SQL replay passed" if replayed else "SQL replay missing"
    return f"{status}. Source table: {table}. Evidence hash recorded."


def action_for_case(case: dict[str, Any], findings: list[dict[str, Any]]) -> tuple[str, str, str]:
    challenges = set(case.get("challenges", []))
    entity = str(case.get("entity", "Unknown"))
    support = case.get("support", {})
    contested = int(support.get("contested", 0) or 0)

    if {"amendment_creep", "vendor_concentration"}.issubset(challenges):
        contract_ref = first_metric(findings, "amendment_creep", "contract_ref")
        multiple_value = first_metric(findings, "amendment_creep", "multiple")
        share = first_metric(findings, "vendor_concentration", "share")
        group = first_metric(findings, "vendor_concentration", "group_key")
        decision = f"Put {entity} into procurement review."
        why = (
            f"{entity} has two independent signals: contract {contract_ref} grew "
            f"{multiple(multiple_value)} and the vendor holds {pct(share)} of {group} spend."
        )
        if contested:
            action = "Pull the contract file, amendment approvals, procurement method, competing bids, and resolve the contested countercheck before escalation."
        else:
            action = "Pull the contract file, amendment approvals, procurement method, and competing bids."
        return decision, why, action

    if "related_parties" in challenges:
        orgs = first_metric(findings, "related_parties", "orgs")
        decision = f"Validate identity for {entity}."
        why = f"{entity} appears across multiple organizations: {orgs}."
        action = "Confirm this is the same person, then check declared conflicts and board relationships."
        return decision, why, action

    decision = f"Review {entity}."
    why = "The system found a reproducible review lead."
    action = "Open the evidence trail, replay the SQL, and assign a human reviewer."
    return decision, why, action


def priority_label(case: dict[str, Any]) -> str:
    support = case.get("support", {})
    if int(support.get("contested", 0) or 0) > 0:
        return "Validate"
    score = int(case.get("score", 0))
    if score >= 25:
        return "Immediate"
    if score >= 15:
        return "Review"
    return "Validate"


def render_action_queue(correlated: dict[str, Any], findings_by_id: dict[str, dict[str, Any]]) -> str:
    cards = []
    for index, case in enumerate(correlated.get("entities", [])[:8], start=1):
        case_findings = [findings_by_id[fid] for fid in case.get("finding_ids", []) if fid in findings_by_id]
        decision, why, action = action_for_case(case, case_findings)
        challenge_tags = "".join(
            f"<span>{esc(CHALLENGE_LABELS.get(ch, ch))}</span>" for ch in case.get("challenges", [])
        )
        proof_items = "".join(f"<li>{esc(proof_line(finding))}</li>" for finding in case_findings)
        check_items = "".join(
            f"<li>{esc(finding.get('support_status', 'not_checked'))}: {esc((finding.get('disconfirming_checks') or [{}])[0].get('question', 'No countercheck recorded'))}</li>"
            for finding in case_findings
        )
        claims = "".join(f"<li>{esc(claim)}</li>" for claim in case.get("claims", []))
        support = case.get("support", {})
        cards.append(
            f"""
      <article class="action-card">
        <div class="rank">{index}</div>
        <div class="action-main">
          <div class="action-top">
            <span class="priority">{esc(priority_label(case))}</span>
            <span class="score">score {esc(case.get("score"))}</span>
            <span class="score">{esc(support.get("supported", 0))} supported · {esc(support.get("contested", 0))} contested</span>
            <div class="tags">{challenge_tags}</div>
          </div>
          <h3>{esc(decision)}</h3>
          <p class="why">{esc(why)}</p>
          <div class="next-action">
            <strong>Next action</strong>
            <p>{esc(action)}</p>
          </div>
          <details>
            <summary>Evidence behind this lead</summary>
            <div class="detail-grid">
              <div>
                <h4>Signals</h4>
                <ul>{claims}</ul>
              </div>
              <div>
                <h4>Replay status</h4>
                <ul>{proof_items}</ul>
              </div>
              <div>
                <h4>Counterchecks</h4>
                <ul>{check_items}</ul>
              </div>
            </div>
          </details>
        </div>
      </article>
"""
        )
    if not cards:
        return "<p class='note'>No review leads yet. Load data, run detectors, then verify findings.</p>"
    return "".join(cards)


def render_decision(correlated: dict[str, Any]) -> str:
    clean = [
        row
        for row in correlated.get("entities", [])
        if int(row.get("score", 0)) >= 25 and int(row.get("support", {}).get("contested", 0) or 0) == 0
    ]
    vendor_leads = [
        row
        for row in correlated.get("entities", [])
        if {"amendment_creep", "vendor_concentration"}.issubset(set(row.get("challenges", [])))
    ]
    validate = [row for row in correlated.get("entities", []) if row not in clean]
    names = ", ".join(str(row.get("entity")) for row in vendor_leads[:3]) or "none yet"
    return (
        "<section class='decision'>"
        "<div class='decision-label'>Decision</div>"
        f"<h2>Start with {len(vendor_leads)} vendor leads: {esc(names)}.</h2>"
        f"<p>{len(clean)} leads are clean escalation-ready. Validate {len(validate)} before escalation. Contested does not mean wrong. It means the next human action is narrower.</p>"
        "</section>"
    )


def render_evidence_table(findings: list[dict[str, Any]]) -> str:
    rows = []
    for finding in findings:
        evidence = (finding.get("evidence") or [{}])[0]
        metrics = evidence.get("metrics") or {}
        metric_bits = []
        if "multiple" in metrics:
            metric_bits.append(f"{float(metrics['multiple']):.1f}x growth")
        if "share" in metrics:
            metric_bits.append(f"{pct(metrics['share'])} share")
        if "org_count" in metrics:
            metric_bits.append(f"{metrics['org_count']} orgs")
        metric_text = ", ".join(metric_bits) or evidence.get("summary", "")
        replayed = finding.get("verification", {}).get("replayed")
        rows.append(
            "<tr>"
            f"<td>{esc(CHALLENGE_LABELS.get(finding.get('challenge'), finding.get('challenge')))}</td>"
            f"<td>{esc(finding.get('entity'))}</td>"
            f"<td>{esc(finding.get('severity'))}</td>"
            f"<td>{esc(metric_text)}</td>"
            f"<td>{'replayed' if replayed else 'not replayed'} · {esc(finding.get('support_status', 'not_checked'))}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_sql_details(findings: list[dict[str, Any]]) -> str:
    blocks = []
    for finding in findings:
        evidence = (finding.get("evidence") or [{}])[0]
        blocks.append(
            "<details class='sql-block'>"
            f"<summary>{esc(finding.get('claim'))}</summary>"
            f"<pre>{esc(evidence.get('sql', ''))}</pre>"
            "</details>"
        )
    return "".join(blocks)


def render_plan(plan: dict[str, Any]) -> str:
    if not plan:
        return "<p class='note'>No investigation plan yet.</p>"
    selected = "".join(
        f"<li><strong>{esc(item.get('skill'))}</strong>: {esc(item.get('reason'))}</li>"
        for item in plan.get("selected", [])
    )
    rejected = "".join(
        f"<li><strong>{esc(item.get('skill'))}</strong>: {esc(item.get('reason'))}</li>"
        for item in plan.get("rejected", [])
    )
    return (
        "<div class='plan-grid'>"
        f"<section class='panel'><h3>Selected by {esc(plan.get('brain'))}</h3><ul>{selected}</ul></section>"
        f"<section class='panel'><h3>Rejected with reasons</h3><ul>{rejected}</ul></section>"
        "</div>"
    )


def render_reviewer(review: dict[str, Any]) -> str:
    if not review:
        return "<p class='note'>No second-pass review yet.</p>"
    issues = review.get("issues", [])
    if issues:
        items = "".join(
            f"<li><strong>{esc(item.get('severity'))}</strong>: {esc(item.get('critique'))}</li>"
            for item in issues
        )
    else:
        items = "<li>No reviewer issues recorded.</li>"
    return (
        "<section class='panel'>"
        f"<h3>{esc(review.get('reviewer'))} second pass</h3>"
        f"<p>{esc(review.get('recommended_language', ''))}</p>"
        f"<ul>{items}</ul>"
        "</section>"
    )


def render() -> str:
    correlated = read_json(paths.findings_dir() / "correlated.json", {"entities": []})
    verified = read_json(paths.findings_dir() / "verified.json", {"findings": []})
    schema = read_json(paths.state_dir() / "discovered.schema.json", [])
    plan = read_json(paths.state_dir() / "investigation-plan.json", {})
    review = read_json(paths.state_dir() / "review.json", {})
    findings = verified.get("findings", [])
    findings_by_id = by_id(findings)
    clean_count = sum(
        1
        for row in correlated.get("entities", [])
        if int(row.get("score", 0)) >= 25 and int(row.get("support", {}).get("contested", 0) or 0) == 0
    )
    vendor_lead_count = sum(
        1
        for row in correlated.get("entities", [])
        if {"amendment_creep", "vendor_concentration"}.issubset(set(row.get("challenges", [])))
    )
    contested_count = sum(1 for row in findings if row.get("support_status") == "contested")
    replayed_count = sum(1 for row in findings if row.get("verification", {}).get("replayed"))
    decision = render_decision(correlated)
    action_queue = render_action_queue(correlated, findings_by_id)
    evidence_rows = render_evidence_table(findings)
    sql_details = render_sql_details(findings)
    plan_html = render_plan(plan)
    reviewer_html = render_reviewer(review)
    schema_json = esc(json.dumps(schema, indent=2)[:6000])

    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Agency 2026 Action Queue</title>
  <style>
    :root {{
      --ink: #191715;
      --muted: #625f59;
      --line: #d8d2c5;
      --paper: #fbfaf7;
      --panel: #ffffff;
      --gold: #9f6b17;
      --red: #9b2f2f;
      --green: #315f49;
      --blue: #254f73;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--paper); color: var(--ink); }}
    header {{ padding: 24px 32px; background: var(--ink); color: var(--paper); }}
    h1 {{ margin: 0 0 8px; font-size: 30px; line-height: 1.1; letter-spacing: 0; }}
    header p {{ margin: 0; max-width: 900px; color: #e5dfd1; font-size: 15px; line-height: 1.5; }}
    main {{ padding: 24px 32px 48px; max-width: 1280px; margin: 0 auto; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 24px; }}
    .metric {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }}
    .metric strong {{ display: block; font-size: 26px; line-height: 1; }}
    .metric span {{ display: block; margin-top: 8px; color: var(--muted); font-size: 13px; }}
    .decision {{ background: #fff; border: 2px solid var(--red); border-radius: 8px; padding: 18px 20px; margin-bottom: 24px; }}
    .decision-label {{ color: var(--red); font-size: 12px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; }}
    .decision h2 {{ margin: 6px 0; font-size: 26px; line-height: 1.2; }}
    .decision p {{ margin: 0; color: var(--muted); line-height: 1.5; }}
    .plan-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 14px 16px; }}
    .panel h3 {{ font-size: 17px; margin-top: 0; }}
    h2 {{ margin: 28px 0 12px; font-size: 20px; }}
    .action-card {{ display: grid; grid-template-columns: 42px 1fr; gap: 14px; background: var(--panel); border: 1px solid var(--line); border-left: 5px solid var(--red); border-radius: 8px; padding: 16px; margin-bottom: 14px; }}
    .rank {{ width: 34px; height: 34px; border-radius: 50%; background: var(--ink); color: var(--paper); display: grid; place-items: center; font-weight: 700; }}
    .action-top {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
    .priority {{ background: #f5dfdf; color: var(--red); border: 1px solid #ddb7b7; border-radius: 999px; padding: 4px 9px; font-size: 12px; font-weight: 700; }}
    .score {{ color: var(--muted); font-size: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
    .tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .tags span {{ background: #eef4f1; color: var(--green); border: 1px solid #c8d9d0; border-radius: 999px; padding: 4px 8px; font-size: 12px; }}
    h3 {{ margin: 10px 0 6px; font-size: 22px; line-height: 1.25; }}
    .why {{ margin: 0 0 12px; color: var(--muted); font-size: 15px; line-height: 1.5; }}
    .next-action {{ background: #f4f7fb; border: 1px solid #c9d7e5; border-radius: 8px; padding: 12px; margin: 12px 0; }}
    .next-action strong {{ color: var(--blue); font-size: 13px; text-transform: uppercase; letter-spacing: .04em; }}
    .next-action p {{ margin: 6px 0 0; line-height: 1.45; }}
    details {{ margin-top: 10px; }}
    summary {{ cursor: pointer; color: var(--gold); font-weight: 700; }}
    .detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 10px; }}
    h4 {{ margin: 0 0 6px; font-size: 14px; }}
    ul {{ margin: 0; padding-left: 18px; color: var(--muted); line-height: 1.45; }}
    table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid var(--line); font-size: 14px; vertical-align: top; }}
    th {{ background: #efede7; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    .sql-block {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; margin-bottom: 10px; }}
    pre {{ max-height: 260px; overflow: auto; background: #111; color: #f5f2ea; padding: 12px; border-radius: 6px; font-size: 12px; line-height: 1.45; }}
    .note {{ color: var(--muted); font-size: 14px; line-height: 1.5; max-width: 900px; }}
    @media (max-width: 820px) {{
      header, main {{ padding-left: 18px; padding-right: 18px; }}
      .summary {{ grid-template-columns: 1fr 1fr; }}
      .plan-grid {{ grid-template-columns: 1fr; }}
      .action-card {{ grid-template-columns: 1fr; }}
      .detail-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>Review these leads first</h1>
    <p>The system converted raw files into a ranked action queue. These are not accusations. They are reproducible review leads with saved SQL, source hashes, and human-review status.</p>
  </header>
  <main>
    <section class="summary">
      <div class="metric"><strong>{vendor_lead_count}</strong><span>vendor leads to start with</span></div>
      <div class="metric"><strong>{clean_count}</strong><span>clean escalation-ready</span></div>
      <div class="metric"><strong>{replayed_count}/{len(findings)}</strong><span>findings replayed</span></div>
      <div class="metric"><strong>{contested_count}</strong><span>contested findings</span></div>
    </section>

    {decision}

    <h2>Agent Plan</h2>
    {plan_html}

    <h2>Second Pass</h2>
    {reviewer_html}

    <h2>Action Queue</h2>
    {action_queue}

    <h2>Finding Register</h2>
    <p class="note">This is the audit register behind the action queue. Every row should be traceable back to a source file and a saved SQL query.</p>
    <table>
      <thead><tr><th>Signal</th><th>Subject</th><th>Severity</th><th>Measured fact</th><th>Replay</th></tr></thead>
      <tbody>{evidence_rows}</tbody>
    </table>

    <h2>Replay Pack</h2>
    <p class="note">Open these only when someone asks how a lead was produced. The pitch should stay on the action queue.</p>
    {sql_details}

    <h2>Loaded Data Shape</h2>
    <details class="sql-block">
      <summary>Schema profile</summary>
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
