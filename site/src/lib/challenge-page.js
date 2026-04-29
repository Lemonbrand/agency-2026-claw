/**
 * Renders a per-challenge page from challenges.json.
 * The HTML page sets <meta name="lc-challenge" content="03"> (id or slug)
 * and provides the empty mount points. This module fills them.
 */

import { loadChallenge, loadAuditSummary, loadExecutionProof } from './manifest.js';
import { renderProofChips, statusLabel } from './proof.js';
import { setDecision, getDecision } from './decisions.js';
import { ask } from './openrouter.js';
import { escText, escAttr, fmtInt, fmtUSD, shortHash } from './data-format.js';

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

function renderRelated(related = []) {
  if (!related.length) return '';
  return `
    <div class="card sp-md">
      <div class="eyebrow">Related findings</div>
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

function renderHeroFinding(c) {
  const f = c.hero_finding || {};
  const bullets = (f.bullets || []).map(b => `<li>${escText(b)}</li>`).join('');
  const metric = f.metric || {};
  return `
    <div class="card accent-orange sp-md">
      <div class="row" style="margin-bottom: 10px;">
        <span class="eyebrow">The finding</span>
        ${c.execution_status?.row_count != null ? `<span class="chip orange" style="margin-left: auto;">${fmtInt(c.execution_status.row_count)} rows</span>` : ''}
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
  if (status.ran) meta.push(`<span class="chip green">probe ran</span>`);
  if (status.row_count != null) meta.push(`<span class="chip">${fmtInt(status.row_count)} rows</span>`);
  if (status.runtime_ms != null) meta.push(`<span class="chip">${status.runtime_ms} ms</span>`);
  if (status.sql_hash) meta.push(`<span class="chip">sha: <code>${escText(shortHash(status.sql_hash))}</code></span>`);

  if (!sql && meta.length === 0) return '';

  return `
    <details class="collapsible sp-md">
      <summary>Replay this finding</summary>
      ${meta.length ? `<div class="row" style="margin-top: 10px;">${meta.join('')}</div>` : ''}
      ${sql ? `<pre style="margin-top: 10px;">${escText(sql)}</pre>` : ''}
      ${(c.tables_joined || []).length ? `
        <div style="margin-top: 10px;">
          <span class="eyebrow">Tables joined</span>
          <div class="row" style="margin-top: 4px;">
            ${c.tables_joined.map(t => `<code>${escText(t)}</code>`).join(' ')}
          </div>
        </div>` : ''}
    </details>
  `;
}

function renderDisconfirm(c) {
  if (!c.disconfirm_check) return '';
  return `
    <div class="card accent-navy sp-md">
      <div class="eyebrow">What would disprove this</div>
      <p style="margin-top: 6px; line-height: 1.6;">${escText(c.disconfirm_check)}</p>
    </div>
  `;
}

function renderRoadblocks(roadblocks = []) {
  if (!roadblocks.length) return '';
  return `
    <div class="card accent-amber sp-md">
      <div class="eyebrow">Roadblocks</div>
      <ul style="margin-left: 18px; margin-top: 8px; line-height: 1.55;">
        ${roadblocks.map(r => `<li>${escText(r)}</li>`).join('')}
      </ul>
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
          <button class="btn btn--success" data-verdict="promote">Promote</button>
          <button class="btn" data-verdict="review">Needs review</button>
          <button class="btn btn--danger" data-verdict="reject">Reject</button>
          <span class="note note--small" style="margin-left: auto;" data-decided-at>${existing.decided_at ? 'last saved ' + new Date(existing.decided_at).toLocaleTimeString() : ''}</span>
        </div>
        <textarea class="decision__note" placeholder="Optional note (saved as you type)">${escText(existing.note || '')}</textarea>
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
      toast(`Saved. ${verdict.charAt(0).toUpperCase() + verdict.slice(1)} → ${challengeId}`);
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

function renderQARail(challengeId, challengeTitle) {
  const q1 = `Why does ${challengeTitle} matter?`;
  const q2 = `What is the strongest evidence for ${challengeTitle}?`;
  const q3 = `What would disprove the finding in ${challengeTitle}?`;
  return `
    <aside class="card sp-md" id="qa-rail">
      <div class="eyebrow">Ask about this loop</div>
      <div class="row" style="gap: 6px; margin: 10px 0;">
        <button class="qa-inline__chip-btn" data-q="${escAttr(q1)}">Why it matters</button>
        <button class="qa-inline__chip-btn" data-q="${escAttr(q2)}">Strongest evidence</button>
        <button class="qa-inline__chip-btn" data-q="${escAttr(q3)}">What would disprove</button>
      </div>
      <select id="qa-rail-model" style="font-size: 13px; padding: 6px 8px; border: 1px solid var(--border); border-radius: 6px; margin-bottom: 8px; width: 100%;">
        <option value="sonnet">Claude Sonnet 4.5 · US</option>
        <option value="opus">Claude Opus 4.1 · US (deep)</option>
        <option value="cohere">Cohere Command A · Sovereign / Canadian</option>
      </select>
      <textarea id="qa-rail-input" rows="2" placeholder="Or type a question scoped to this loop." style="width: 100%; font-family: 'DM Sans'; font-size: 13px; border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; resize: vertical;"></textarea>
      <button class="btn btn--primary" id="qa-rail-submit" style="margin-top: 8px; width: 100%;">Ask</button>
      <div id="qa-rail-answer" style="margin-top: 12px; font-size: 13px; line-height: 1.5; white-space: pre-wrap; color: var(--ink-2);"></div>
      <div id="qa-rail-meta" class="qa-inline__meta" style="margin-top: 8px;"></div>
    </aside>
  `;
}

function wireQARail(root, challengeId) {
  const input = root.querySelector('#qa-rail-input');
  const sel = root.querySelector('#qa-rail-model');
  const submit = root.querySelector('#qa-rail-submit');
  const answer = root.querySelector('#qa-rail-answer');
  const meta = root.querySelector('#qa-rail-meta');

  root.querySelectorAll('.qa-inline__chip-btn').forEach(btn => {
    btn.addEventListener('click', () => { input.value = btn.dataset.q; run(); });
  });
  submit.addEventListener('click', run);

  async function run() {
    const q = input.value.trim();
    if (!q) return;
    answer.textContent = '';
    meta.textContent = `Asking · ${sel.value}`;
    submit.disabled = true;
    try {
      const r = await ask({
        question: q,
        scope: `challenge:${challengeId}`,
        model: sel.value,
        onChunk: chunk => { answer.textContent += chunk; },
      });
      if (!answer.textContent) answer.textContent = r.answer || '(no answer)';
      meta.innerHTML = [
        `<span>via <code>${escText(r.via)}</code></span>`,
        `<span>${escText(r.model)}</span>`,
        `<span>in ${fmtInt(r.tokens_in)} · out ${fmtInt(r.tokens_out)}</span>`,
        `<span>${fmtUSD(r.cost_usd, 4)}</span>`,
      ].join('');
    } catch (err) {
      answer.textContent = `Could not ask: ${err.message}`;
      meta.textContent = '';
    } finally {
      submit.disabled = false;
    }
  }
}

export async function renderChallengePage() {
  const id = getChallengeId();
  if (!id) {
    document.querySelector('main').innerHTML = `<p class="empty">No challenge id specified.</p>`;
    return;
  }

  const [challenge, audit, proofs] = await Promise.all([
    loadChallenge(id),
    loadAuditSummary(),
    loadExecutionProof(),
  ]);

  if (!challenge) {
    document.querySelector('main').innerHTML = `
      <div class="card accent-amber">
        <h2>This loop is loading.</h2>
        <p class="note">The backend bundle does not yet contain challenge <code>${escText(id)}</code>. The page will fill in once <code>challenges.json</code> includes it. Reload in a minute.</p>
      </div>`;
    return;
  }

  const auditEntry = findAuditEntry(audit, challenge.id);
  const proofEntry = findExecutionProof(proofs, challenge.id);

  document.title = `${challenge.title} — Agency 2026`;

  const main = document.querySelector('main');
  main.innerHTML = `
    <div class="row sp-md">
      <span class="chip primary">Loop ${escText(challenge.id || challenge.number)}</span>
      <span class="chip ${statusToCls(challenge.status)}">${escText(statusLabel(challenge.status))}</span>
      ${renderProofChips(challenge.proof_levels || [])}
      ${auditEntry ? `<span class="chip ${verdictCls(auditEntry.verdict)}" title="Lexical audit verdict">audit: ${escText(auditEntry.verdict)}</span>` : ''}
      <a href="/explore/audit.html#challenge-${escAttr(challenge.id)}" class="chip" style="margin-left: auto;">View in audit ↗</a>
    </div>

    <h1 class="sp-md">${escText(challenge.title)}</h1>
    ${challenge.subtitle ? `<p class="lede">${escText(challenge.subtitle)}</p>` : ''}

    <div class="grid" style="grid-template-columns: 1fr 320px; gap: 24px;" id="challenge-grid">
      <div>
        ${challenge.brief_excerpt ? `
          <div class="card sp-md" style="background: var(--navy-wash); border-color: var(--navy-border);">
            <div class="eyebrow" style="color: var(--navy);">Challenge as posed</div>
            <p style="font-style: italic; color: var(--navy-deep); line-height: 1.55; margin-top: 6px;">${escText(challenge.brief_excerpt)}</p>
          </div>
        ` : ''}

        ${challenge.presentation_sentence ? `
          <div class="sp-md">
            <div class="eyebrow">AI-native pattern</div>
            <p style="margin-top: 6px; line-height: 1.6;">${escText(challenge.presentation_sentence)}</p>
          </div>
        ` : ''}

        ${renderHeroFinding(challenge)}
        ${renderRoadblocks(challenge.roadblocks)}
        ${renderReplay(challenge)}
        ${renderDisconfirm(challenge)}

        ${proofEntry?.missing && (proofEntry.missing.tables?.length || proofEntry.missing.fields?.length || proofEntry.missing.external_sources?.length) ? `
          <div class="card accent-gray sp-md">
            <div class="eyebrow">What is missing to run this further</div>
            ${proofEntry.missing.tables?.length ? `<p style="margin-top: 8px;"><strong>Tables:</strong> ${proofEntry.missing.tables.map(t => `<code>${escText(t)}</code>`).join(' ')}</p>` : ''}
            ${proofEntry.missing.fields?.length ? `<p><strong>Fields:</strong> ${proofEntry.missing.fields.map(t => `<code>${escText(t)}</code>`).join(' ')}</p>` : ''}
            ${proofEntry.missing.external_sources?.length ? `<p><strong>External sources:</strong> ${proofEntry.missing.external_sources.map(s => escText(s)).join(' · ')}</p>` : ''}
          </div>
        ` : ''}

        ${renderDecisionPanel(challenge.id, challenge.decision_prompt)}
        ${renderRelated(challenge.related_findings)}
      </div>
      <div>
        ${renderQARail(challenge.id, challenge.title)}
      </div>
    </div>
  `;

  wireDecisionPanel(main, challenge.id);
  wireQARail(main, challenge.id);

  // Mobile: collapse the right rail under the main column
  const mq = window.matchMedia('(max-width: 880px)');
  function applyResponsive() {
    const grid = main.querySelector('#challenge-grid');
    if (mq.matches) grid.style.gridTemplateColumns = '1fr';
    else grid.style.gridTemplateColumns = '1fr 320px';
  }
  applyResponsive();
  mq.addEventListener('change', applyResponsive);
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
