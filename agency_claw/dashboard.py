from __future__ import annotations

import html
import json

from . import paths
from .jsonio import read_json


def render() -> str:
    correlated = read_json(paths.findings_dir() / "correlated.json", {"entities": []})
    verified = read_json(paths.findings_dir() / "verified.json", {"findings": []})
    schema = read_json(paths.state_dir() / "discovered.schema.json", [])
    findings = verified.get("findings", [])

    rows = []
    for item in correlated.get("entities", []):
        rows.append(
            f"<tr><td>{html.escape(item['entity'])}</td><td>{item['score']}</td><td>{item['challenge_count']}</td><td>{html.escape(', '.join(item['challenges']))}</td></tr>"
        )

    finding_cards = []
    for finding in findings:
        evidence = finding.get("evidence", [{}])[0]
        finding_cards.append(
            "<article>"
            f"<div class='meta'>{html.escape(finding.get('challenge', ''))} · {html.escape(finding.get('severity', ''))} · {html.escape(finding.get('status', ''))}</div>"
            f"<h3>{html.escape(finding.get('claim', ''))}</h3>"
            f"<p>{html.escape(evidence.get('summary', ''))}</p>"
            f"<pre>{html.escape(evidence.get('sql', ''))}</pre>"
            "</article>"
        )

    schema_json = html.escape(json.dumps(schema, indent=2)[:6000])
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Agency 2026 Claw</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f7f4ec; color: #191715; }}
    header {{ padding: 24px 32px; background: #191715; color: #f7f4ec; display: flex; justify-content: space-between; align-items: end; }}
    h1 {{ margin: 0; font-size: 28px; }}
    .counter {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; color: #d9c9a3; }}
    main {{ display: grid; grid-template-columns: 1fr 1.2fr; gap: 24px; padding: 24px 32px; }}
    section {{ min-width: 0; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #e2ded4; font-size: 14px; }}
    article {{ background: white; border: 1px solid #e2ded4; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
    h2 {{ font-size: 18px; }}
    h3 {{ margin: 8px 0; font-size: 17px; }}
    .meta {{ color: #7b5d36; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    pre {{ max-height: 220px; overflow: auto; background: #191715; color: #f7f4ec; padding: 12px; border-radius: 6px; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Agency 2026 Claw</h1>
      <div class="counter">local DuckDB · local Neotoma · replayable evidence</div>
    </div>
    <div class="counter">findings: {len(findings)} · tables: {len(schema)}</div>
  </header>
  <main>
    <section>
      <h2>Correlated Leads</h2>
      <table>
        <thead><tr><th>Entity</th><th>Score</th><th>Signals</th><th>Challenges</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
      <h2>Schema Profile</h2>
      <pre>{schema_json}</pre>
    </section>
    <section>
      <h2>Evidence Trails</h2>
      {''.join(finding_cards)}
    </section>
  </main>
</body>
</html>
"""


def write_dashboard() -> str:
    paths.ensure_dirs()
    out = paths.web_dir() / "dashboard.html"
    out.write_text(render())
    return str(out)
