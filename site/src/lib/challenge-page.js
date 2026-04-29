/**
 * Renders a per-challenge page from challenges.json.
 * The HTML page sets <meta name="lc-challenge" content="03"> (id or slug)
 * and provides the empty mount points. This module fills them.
 */

import { loadChallenge, loadAuditSummary, loadExecutionProof, loadFindingsIndex, loadChallenges } from './manifest.js';
import { renderProofChips, statusLabel } from './proof.js';
import { setDecision, getDecision } from './decisions.js';
import { openFindingDrawer } from './finding-drawer.js';
import { escText, escAttr, fmtInt, fmtUSD, fmtCAD, shortHash } from './data-format.js';

function getChallengeId() {
  const meta = document.querySelector('meta[name="lc-challenge"]');
  return meta?.content || (location.pathname.match(/challenges\/([^.]+)\.html/) || [])[1];
}

function findExecutionProof(proofs, id) {
  return (proofs || []).find(p => p.challenge_id === id || p.challenge_id === String(id));
}

function findAuditEntry(audit, id) {
  return (audit?.per_challenge || []).find(p => p.id === id || p.id === String(id));
}

function sourceLink(table) {
  const q = encodeURIComponent(table);
  return `<a href="/explore/data-tables.html?q=${q}" title="Search findings using this source table"><code>${escText(table)}</code></a>`;
}

function renderRelated(related = []) {
  if (!related.length) return '';
  return `
    <div class="card sp-md">
      <div class="eyebrow">Related leads in other checks</div>
      ${related.map(r => `
        <div class="row" style="padding: 6px 0; border-bottom: 1px dashed var(--border);">
          <a href="/challenges/${escAttr(r.challenge_id)}.html" class="mono" style="font-size: 12px;">${escText(r.challenge_id)}</a>
          <span style="font-size: 13px;">${escText(r.entity)}</span>
          <span class="note note--small" style="margin-left: auto;">${escText(r.why || '')}</span>
        </div>
      `).join('')}
    </div>
  `;
}

function sevCls(s) {
  switch ((s || '').toLowerCase()) {
    case 'high':   return 'red';
    case 'medium': return 'amber';
    case 'low':    return 'green';
    default:       return 'gray';
  }
}

function emptyMessageForStatus(challenge) {
  const status = (challenge.status || '').toLowerCase();
  const proofs = (challenge.proof_levels || []).map(p => (p || '').toLowerCase());
  if (status === 'refused' || proofs.includes('refused')) {
    return {
      headline: 'The system refused to claim a finding here.',
      body: 'The data did not contain what was needed to answer this check. Each refusal names the data that would change the answer. See the roadblocks above.',
    };
  }
  if (status === 'external' || proofs.includes('external-needed')) {
    return {
      headline: 'No findings yet — outside data is needed.',
      body: 'This check needs data the GovAlta dataset does not include. Once the outside source lands, leads will populate here.',
    };
  }
  if (status === 'materialized' || proofs.includes('materialized')) {
    return {
      headline: 'No findings yet — needs a materialized dataset.',
      body: 'This check needs a prepared subset or computed column to run. Once that materializes, leads will populate here.',
    };
  }
  return {
    headline: 'No findings yet for this check.',
    body: 'Either the run did not produce a lead, or the index has not caught up. Reload in a minute.',
  };
}

function renderChallengeFindings(findings, challenge, allChallenges) {
  const byId = new Map();
  for (const f of findings) byId.set(f.finding_id, f);

  if (!findings.length) {
    const msg = emptyMessageForStatus(challenge);
    return `
      <div class="card accent-gray sp-md">
        <div class="eyebrow">Review leads in this check</div>
        <h3 style="font-family: 'Outfit', sans-serif; font-weight: 700; font-size: 18px; line-height: 1.25; color: var(--ink); margin-top: 6px;">${escText(msg.headline)}</h3>
        <p class="note" style="margin-top: 8px; line-height: 1.55;">${escText(msg.body)}</p>
      </div>
    `;
  }

  const rows = findings.map((f, i) => {
    const id = f.finding_id || `${f.challenge_id}-${i}`;
    const sev = (f.severity || '').toLowerCase();
    const metric = f.top_metric ? `<span class="note note--small" style="font-family: 'JetBrains Mono', monospace;">${escText(f.top_metric.label || '')}: <strong style="color: var(--ink);">${escText(f.top_metric.value || '')}</strong></span>` : '';
    return `
      <div class="lead-row" data-finding="${escAttr(id)}" tabindex="0" role="button" aria-label="Open details for ${escAttr(f.entity || 'finding')}">
        <div class="lead-row__head">
          <strong class="lead-row__entity">${escText(f.entity || 'Unnamed entity')}</strong>
          ${sev ? `<span class="chip ${sevCls(sev)}" style="font-size: 10px; padding: 1px 7px;">${escText(sev)}</span>` : ''}
          <span class="lead-row__cta">Open ›</span>
        </div>
        ${f.headline ? `<p class="lead-row__line">${escText(f.headline)}</p>` : ''}
        ${metric ? `<div style="margin-top: 6px;">${metric}</div>` : ''}
      </div>
    `;
  }).join('');

  return `
    <div class="lead-list sp-md">
      <div class="row" style="margin-bottom: 10px; align-items: baseline;">
        <div class="eyebrow">Review leads in this check</div>
        <span class="note note--small" style="margin-left: auto; font-family: 'JetBrains Mono', monospace; font-size: 11px;">${findings.length} lead${findings.length === 1 ? '' : 's'} · click any row for the full detail</span>
      </div>
      <div class="lead-list__grid">${rows}</div>
    </div>
  `;
}

function wireChallengeFindings(root, findings, allChallenges) {
  const byId = new Map();
  for (const f of findings) byId.set(f.finding_id, f);
  root.querySelectorAll('.lead-row[data-finding]').forEach(el => {
    const id = el.getAttribute('data-finding');
    const open = () => {
      const f = byId.get(id);
      if (f) openFindingDrawer(f, { challenges: allChallenges });
    };
    el.addEventListener('click', open);
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open(); }
    });
  });
}

function renderHeroFinding(c) {
  const f = c.hero_finding || {};
  const bullets = (f.bullets || []).map(b => `<li>${escText(b)}</li>`).join('');
  const metric = f.metric || {};
  return `
    <div class="card accent-orange sp-md">
      <div class="row" style="margin-bottom: 10px;">
        <span class="eyebrow">Review lead</span>
        ${c.execution_status?.row_count != null ? `<span class="chip orange" style="margin-left: auto;">${fmtInt(c.execution_status.row_count)} records returned</span>` : ''}
      </div>
      ${f.entity ? `<h3 style="font-size: 22px; margin-bottom: 8px;">${escText(f.entity)}</h3>` : ''}
      ${metric.value ? `<div style="font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--ink-2); margin-bottom: 10px;">${escText(metric.label || '')} <strong style="color: var(--ink); font-size: 18px;">${escText(metric.value)}</strong></div>` : ''}
      ${bullets ? `<ul style="margin-left: 18px; line-height: 1.6;">${bullets}</ul>` : ''}
      ${f.pattern ? `<p class="note" style="margin-top: 12px; font-style: italic;">${escText(f.pattern)}</p>` : ''}
    </div>
  `;
}

function renderReplay(c) {
  const sql = c.replay_sql || '';
  const status = c.execution_status || {};
  const meta = [];
  if (status.ran) meta.push(`<span class="chip green">query ran</span>`);
  if (status.row_count != null) meta.push(`<span class="chip">${fmtInt(status.row_count)} records returned</span>`);
  if (status.runtime_ms != null) meta.push(`<span class="chip">${status.runtime_ms} ms runtime</span>`);
  if (status.sql_hash) meta.push(`<span class="chip">fingerprint: <code>${escText(shortHash(status.sql_hash))}</code></span>`);

  if (!sql && meta.length === 0) return '';

  return `
    <details class="collapsible sp-md">
      <summary>Evidence and query</summary>
      ${meta.length ? `<div class="row" style="margin-top: 10px;">${meta.join('')}</div>` : ''}
      ${sql ? `<pre style="margin-top: 10px;">${escText(sql)}</pre>` : ''}
      ${(c.tables_joined || []).length ? `
        <div style="margin-top: 10px;">
          <span class="eyebrow">Source data</span>
          <div class="row" style="margin-top: 4px;">
            ${c.tables_joined.map(sourceLink).join(' ')}
          </div>
        </div>` : ''}
    </details>
  `;
}

function renderDisconfirm(c) {
  if (!c.disconfirm_check) return '';
  return `
    <div class="card accent-navy sp-md">
      <div class="eyebrow">Countercheck</div>
      <p style="margin-top: 6px; line-height: 1.6;">${escText(c.disconfirm_check)}</p>
    </div>
  `;
}

function renderRoadblocks(roadblocks = []) {
  if (!roadblocks.length) return '';
  return `
    <div class="card accent-amber sp-md">
      <div class="eyebrow">What we still need</div>
      <ul style="margin-left: 18px; margin-top: 8px; line-height: 1.55;">
        ${roadblocks.map(r => `<li>${escText(r)}</li>`).join('')}
      </ul>
    </div>
  `;
}

function renderEvidenceLegend(c) {
  const tableCount = (c.tables_joined || []).length;
  const query = c.execution_status || {};
  return `
    <div class="card sp-md">
      <div class="eyebrow">How to read this page</div>
      <div style="display: grid; gap: 10px; margin-top: 10px; font-size: 13px; line-height: 1.45; color: var(--ink-2);">
        <div><strong style="color: var(--ink);">Source data</strong> means the tables or datasets the check read. ${tableCount ? `${fmtInt(tableCount)} source ${tableCount === 1 ? 'table is' : 'tables are'} linked below.` : 'No source table is attached yet.'}</div>
        <div><strong style="color: var(--ink);">Evidence status</strong> says whether the data fields were verified, the query ran, or an outside source is still needed.</div>
        <div><strong style="color: var(--ink);">Query proof</strong> is the receipt: ${query.sql_hash ? `fingerprint ${escText(shortHash(query.sql_hash))}, ` : ''}${query.runtime_ms != null ? `${query.runtime_ms} ms runtime, ` : ''}${query.row_count != null ? `${fmtInt(query.row_count)} records came back.` : 'not yet run.'}</div>
      </div>
    </div>
  `;
}

function renderDecisionPanel(challengeId, prompt) {
  const existing = getDecision(challengeId) || {};
  const verdict = existing.verdict || '';
  return `
    <div class="card sp-md">
      <div class="eyebrow">Your decision</div>
      ${prompt ? `<p style="margin: 8px 0 12px; color: var(--ink-2);">${escText(prompt)}</p>` : ''}
      <div class="decision" data-verdict="${escAttr(verdict)}">
        <div class="decision__row">
          <button class="btn btn--success" data-verdict="promote">Escalate</button>
          <button class="btn" data-verdict="review">Hold for review</button>
          <button class="btn btn--danger" data-verdict="reject">Close</button>
          <span class="note note--small" style="margin-left: auto;" data-decided-at>${existing.decided_at ? 'last saved ' + new Date(existing.decided_at).toLocaleTimeString() : ''}</span>
        </div>
        <textarea class="decision__note" placeholder="Optional note (saved as you type)">${escText(existing.note || '')}</textarea>
      </div>
    </div>
  `;
}

function askUrl(challenge, question, { autorun = true } = {}) {
  const params = new URLSearchParams();
  params.set('scope', `challenge:${challenge.id}`);
  params.set('q', question);
  if (autorun) params.set('ask', '1');
  return `/explore/ask.html?${params.toString()}`;
}

function renderAskPanel(challenge) {
  const label = `Check ${challenge.id} ${challenge.title}`;
  const questions = [
    {
      label: 'Explain this check',
      q: `For ${label}, explain what this check found in plain English, with the source tables and proof level.`,
    },
    {
      label: 'Strongest evidence',
      q: `For ${label}, what is the strongest evidence in the current packet, and what receipt proves it?`,
    },
    {
      label: 'Countercheck',
      q: `For ${label}, what countercheck could weaken or disprove the review lead?`,
    },
    {
      label: 'Missing evidence',
      q: `For ${label}, what data is still missing before a reviewer should escalate this?`,
    },
  ];
  return `
    <div class="card sp-md" style="background: var(--paper-2);">
      <div class="row" style="align-items: flex-start; gap: 14px;">
        <div style="flex: 1 1 280px;">
          <div class="eyebrow">Ask about this check</div>
          <p class="note" style="margin-top: 6px;">Open the evidence chat with this check already scoped. The question is carried into the Ask page and submitted with its proof trail.</p>
        </div>
        <a class="btn" data-ask-open="true" href="${escAttr(askUrl(challenge, `For ${label}, what should a reviewer ask next?`, { autorun: false }))}">Open Ask ›</a>
      </div>
      <div class="row" style="margin-top: 14px;">
        ${questions.map(item => `<a class="btn btn--primary" href="${escAttr(askUrl(challenge, item.q))}" data-ask-question="${escAttr(item.q)}">${escText(item.label)}</a>`).join('')}
      </div>
    </div>
  `;
}

function wireDecisionPanel(root, challengeId) {
  const panel = root.querySelector('.decision');
  if (!panel) return;
  const note = root.querySelector('.decision__note');
  const decided = root.querySelector('[data-decided-at]');

  panel.querySelectorAll('button[data-verdict]').forEach(btn => {
    btn.addEventListener('click', () => {
      const verdict = btn.dataset.verdict;
      panel.dataset.verdict = verdict;
      const saved = setDecision(challengeId, verdict, note?.value || '');
      if (decided) decided.textContent = 'last saved ' + new Date(saved.decided_at).toLocaleTimeString();
      const label = { promote: 'Escalate', review: 'Hold for review', reject: 'Close' }[verdict] || verdict;
      toast(`Saved. ${label} -> ${challengeId}`);
    });
  });

  if (note) {
    let timer = null;
    note.addEventListener('input', () => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        const verdict = panel.dataset.verdict;
        if (verdict) {
          const saved = setDecision(challengeId, verdict, note.value);
          if (decided) decided.textContent = 'last saved ' + new Date(saved.decided_at).toLocaleTimeString();
        }
      }, 350);
    });
  }
}

function toast(message) {
  let host = document.getElementById('lc-toast-host');
  if (!host) {
    host = document.createElement('div');
    host.id = 'lc-toast-host';
    host.style.cssText = 'position:fixed;bottom:24px;right:24px;display:grid;gap:8px;z-index:1000;';
    document.body.appendChild(host);
  }
  const el = document.createElement('div');
  el.textContent = message;
  el.style.cssText = 'background:var(--ink);color:var(--paper);padding:10px 14px;border-radius:8px;font-size:13px;font-family:"DM Sans",sans-serif;box-shadow:var(--shadow-md);animation:pasteIn .25s ease;';
  host.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }, 2200);
}

export async function renderChallengePage() {
  const id = getChallengeId();
  if (!id) {
    document.querySelector('main').innerHTML = `<p class="empty">No challenge id specified.</p>`;
    return;
  }

  const [challenge, audit, proofs, findings, allChallenges] = await Promise.all([
    loadChallenge(id),
    loadAuditSummary(),
    loadExecutionProof(),
    loadFindingsIndex(),
    loadChallenges(),
  ]);

  if (!challenge) {
    document.querySelector('main').innerHTML = `
      <div class="card accent-amber">
        <h2>This check is loading.</h2>
        <p class="note">The evidence bundle does not yet contain check <code>${escText(id)}</code>. The page will fill in once <code>challenges.json</code> includes it. Reload in a minute.</p>
      </div>`;
    return;
  }

  const auditEntry = findAuditEntry(audit, challenge.id);
  const proofEntry = findExecutionProof(proofs, challenge.id);
  // Findings index uses combined "<id>-<slug>" form (e.g. "03-funding-loops"),
  // while challenges.json keys by short id ("03") + separate slug ("funding-loops").
  const idSlug = challenge.slug ? `${challenge.id}-${challenge.slug}` : challenge.id;
  const challengeFindings = (findings || []).filter(f => {
    const cid = f.challenge_id;
    return cid === challenge.id
      || cid === String(challenge.id)
      || cid === idSlug
      || cid === challenge.slug;
  });

  document.title = `${challenge.title} | Agency 2026`;

  const main = document.querySelector('main');
  main.innerHTML = `
    <div class="row sp-md">
      <span class="chip primary">Check ${escText(challenge.id || challenge.number)}</span>
      <span class="chip ${statusToCls(challenge.status)}">${escText(statusLabel(challenge.status))}</span>
      ${renderProofChips(challenge.proof_levels || [])}
      ${auditEntry ? `<span class="chip ${verdictCls(auditEntry.verdict)}" title="Evidence-trail verdict">evidence trail: ${escText(auditEntry.verdict)}</span>` : ''}
      <a href="/explore/audit.html#challenge-${escAttr(challenge.id)}" class="chip" style="margin-left: auto;">Open evidence trail ↗</a>
    </div>

    <h1 class="sp-md">${escText(challenge.title)}</h1>
    ${challenge.subtitle ? `<p class="lede">${escText(challenge.subtitle)}</p>` : ''}

    <div id="challenge-body">
      ${challenge.brief_excerpt ? `
        <div class="card sp-md" style="background: var(--navy-wash); border-color: var(--navy-border);">
          <div class="eyebrow" style="color: var(--navy);">Accountability question</div>
          <p style="font-style: italic; color: var(--navy-deep); line-height: 1.55; margin-top: 6px;">${escText(challenge.brief_excerpt)}</p>
        </div>
      ` : ''}

      ${challenge.presentation_sentence ? `
        <div class="sp-md">
          <div class="eyebrow">How this check works</div>
          <p style="margin-top: 6px; line-height: 1.6;">${escText(challenge.presentation_sentence)}</p>
        </div>
      ` : ''}

      ${renderEvidenceLegend(challenge)}
      ${renderHeroFinding(challenge)}
      ${renderChallengeFindings(challengeFindings, challenge, allChallenges)}
      ${renderRoadblocks(challenge.roadblocks)}
      ${renderReplay(challenge)}
      ${renderDisconfirm(challenge)}

      ${proofEntry?.missing && (proofEntry.missing.tables?.length || proofEntry.missing.fields?.length || proofEntry.missing.external_sources?.length) ? `
        <div class="card accent-gray sp-md">
          <div class="eyebrow">Missing evidence</div>
          ${proofEntry.missing.tables?.length ? `<p style="margin-top: 8px;"><strong>Source tables:</strong> ${proofEntry.missing.tables.map(sourceLink).join(' ')}</p>` : ''}
          ${proofEntry.missing.fields?.length ? `<p><strong>Fields:</strong> ${proofEntry.missing.fields.map(t => `<code>${escText(t)}</code>`).join(' ')}</p>` : ''}
          ${proofEntry.missing.external_sources?.length ? `<p><strong>Outside sources:</strong> ${proofEntry.missing.external_sources.map(s => escText(s)).join(' · ')}</p>` : ''}
        </div>
      ` : ''}

      ${renderDecisionPanel(challenge.id, challenge.decision_prompt)}
      ${renderRelated(challenge.related_findings)}

      ${renderAskPanel(challenge)}
    </div>
  `;

  wireDecisionPanel(main, challenge.id);
  wireChallengeFindings(main, challengeFindings, allChallenges);
}

function statusToCls(status) {
  switch ((status || '').toLowerCase()) {
    case 'runnable':     return 'green';
    case 'materialized': return 'amber';
    case 'external':     return 'gray';
    case 'refused':      return 'gray';
    default:             return 'gray';
  }
}

function verdictCls(verdict) {
  switch ((verdict || '').toLowerCase()) {
    case 'clean':  return 'green';
    case 'review': return 'amber';
    case 'unsafe': return 'red';
    default:       return 'gray';
  }
}
