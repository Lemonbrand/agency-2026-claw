/*
 * Side drawer for finding details. Opens from the right with a backdrop.
 * Closes on ESC, backdrop click, or the close button. One drawer per page.
 */
import { escText, escAttr, shortHash, fmtInt } from './data-format.js';
import { setDecision } from './decisions.js';

let _backdrop, _drawer, _previousFocus;

function ensureMounted() {
  if (_drawer) return;
  _backdrop = document.createElement('div');
  _backdrop.className = 'drawer-backdrop';
  _backdrop.addEventListener('click', closeDrawer);

  _drawer = document.createElement('aside');
  _drawer.className = 'drawer';
  _drawer.setAttribute('role', 'dialog');
  _drawer.setAttribute('aria-modal', 'true');
  _drawer.setAttribute('aria-labelledby', 'drawer-title');
  _drawer.setAttribute('tabindex', '-1');

  document.body.appendChild(_backdrop);
  document.body.appendChild(_drawer);

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && _drawer.classList.contains('is-open')) closeDrawer();
  });
}

function sevCls(s) {
  switch ((s || '').toLowerCase()) {
    case 'high':   return 'red';
    case 'medium': return 'amber';
    case 'low':    return 'green';
    default:       return 'gray';
  }
}
function supCls(s) {
  switch ((s || '').toLowerCase()) {
    case 'supported':    return 'green';
    case 'contested':    return 'red';
    case 'inconclusive': return 'amber';
    default:             return 'gray';
  }
}
function supLabel(s) {
  switch ((s || '').toLowerCase()) {
    case 'supported':    return 'Supported';
    case 'contested':    return 'Contested';
    case 'inconclusive': return 'Inconclusive';
    case 'not_checked':  return 'Needs reviewer check';
    default:             return s ? String(s).replaceAll('_', ' ') : '';
  }
}

function challengeSlug(challengeId, challenges = []) {
  const c = challenges.find(x => x.id === challengeId || x.slug === challengeId);
  return c?.slug || challengeId;
}

export function openFindingDrawer(finding, ctx = {}) {
  ensureMounted();
  _previousFocus = document.activeElement;

  const sev = (finding.severity || '').toLowerCase();
  const sup = (finding.support_status || '').toLowerCase();
  const fp  = finding.sha ? shortHash(finding.sha) : '';
  const cid = finding.challenge_id || '';
  const cidShort = (cid || '').split('-')[0];
  const slug = challengeSlug(cid, ctx.challenges || []);
  const challengeTitle = ctx.challengeTitle ||
    (ctx.challenges || []).find(c => c.id === cid)?.title || '';

  const headLine = ctx.eyebrow ||
    (cidShort ? `Check ${cidShort}${challengeTitle ? ' · ' + challengeTitle : ''}` : 'Finding');

  const isCross = !!ctx.crossEntries?.length;
  const crossList = isCross
    ? ctx.crossEntries.map(e => {
        const t = e.title || e.challenge_id;
        return `<a href="/challenges/${escAttr(challengeSlug(e.challenge_id, ctx.challenges || []))}.html" style="color:var(--navy);border-bottom:1px dotted var(--navy-border);font-size:13px;line-height:1.5;">${escText(t)}</a>`;
      }).join(' · ')
    : '';

  _drawer.innerHTML = `
    <div class="drawer__head">
      <div>
        <span class="eyebrow">${escText(headLine)}</span>
        <h2 id="drawer-title">${escText(finding.entity || 'Unnamed entity')}</h2>
      </div>
      <button class="drawer__close" aria-label="Close">×</button>
    </div>
    <div class="drawer__body">
      ${finding.headline ? `<p style="font-size:15px;line-height:1.55;color:var(--ink);">${escText(finding.headline)}</p>` : ''}
      ${finding.top_metric ? `
        <div class="drawer__metric">
          <div class="k">${escText(finding.top_metric.label || 'Top metric')}</div>
          <div class="v">${escText(finding.top_metric.value || '')}</div>
        </div>
      ` : ''}
      ${isCross ? `
        <div class="drawer__row">
          <span class="k">Surfaces in</span>
          <span class="v">${crossList}</span>
        </div>
      ` : ''}
      <div style="display:grid; gap:10px;">
        ${sev ? `<div class="drawer__row"><span class="k">Severity</span><span class="v"><span class="chip ${sevCls(sev)}">${escText(sev)}</span></span></div>` : ''}
        ${sup ? `<div class="drawer__row"><span class="k">Support</span><span class="v"><span class="chip ${supCls(sup)}" title="${escAttr(sup === 'not_checked' ? 'The support-audit pass has not run on this check yet. The lead has not been disconfirmed; it has just not been independently verified.' : '')}">${escText(supLabel(sup))}</span>${sup === 'not_checked' ? `<div style="margin-top:4px;font-size:11.5px;color:var(--ink-3);line-height:1.45;">The support-audit pass has only run on check 05 so far. Other checks read <em>Needs reviewer check</em> until that pass extends to them.</div>` : ''}</span></div>` : ''}
        ${(finding.source_tables || []).length ? `<div class="drawer__row"><span class="k">Source data</span><span class="v">${finding.source_tables.map(t => `<code>${escText(t)}</code>`).join(' · ')}</span></div>` : ''}
        ${fp ? `<div class="drawer__row"><span class="k">Receipt</span><span class="v"><code>${escText(fp)}</code></span></div>` : ''}
        ${finding.finding_id ? `<div class="drawer__row"><span class="k">Finding id</span><span class="v"><code>${escText(finding.finding_id)}</code></span></div>` : ''}
      </div>
      <p style="font-size:12.5px;color:var(--ink-3);line-height:1.5;margin-top:4px;">Open the full check to see the source data, the read-only query, and the countercheck the system used.</p>
    </div>
    <div class="drawer__foot">
      ${cid ? `<a class="btn btn--primary" href="/challenges/${escAttr(slug)}.html">Open the full check ›</a>` : ''}
      ${cid ? `<button class="btn" data-action="mark-review">Mark for review</button>` : ''}
      <button class="btn" data-action="close" style="margin-left:auto;">Close</button>
    </div>
  `;

  _drawer.querySelector('.drawer__close').addEventListener('click', closeDrawer);
  _drawer.querySelector('[data-action="close"]').addEventListener('click', closeDrawer);
  const reviewBtn = _drawer.querySelector('[data-action="mark-review"]');
  if (reviewBtn) {
    reviewBtn.addEventListener('click', () => {
      try {
        setDecision(cid, 'review', `Marked from drawer · ${finding.entity || ''}`);
        toast(`Marked ${cidShort} for review.`);
      } catch (err) {
        toast('Could not save.');
      }
      closeDrawer();
    });
  }

  requestAnimationFrame(() => {
    _backdrop.classList.add('is-open');
    _drawer.classList.add('is-open');
    document.documentElement.style.overflow = 'hidden';
    _drawer.querySelector('.drawer__close')?.focus();
  });
}

export function closeDrawer() {
  if (!_drawer) return;
  _drawer.classList.remove('is-open');
  _backdrop.classList.remove('is-open');
  document.documentElement.style.overflow = '';
  if (_previousFocus && typeof _previousFocus.focus === 'function') _previousFocus.focus();
}

function toast(message) {
  let host = document.getElementById('lc-toast-host');
  if (!host) {
    host = document.createElement('div');
    host.id = 'lc-toast-host';
    host.style.cssText = 'position:fixed;bottom:24px;right:24px;display:grid;gap:8px;z-index:1300;';
    document.body.appendChild(host);
  }
  const el = document.createElement('div');
  el.textContent = message;
  el.style.cssText = 'background:var(--ink);color:var(--paper);padding:10px 14px;border-radius:8px;font-size:13px;font-family:"DM Sans",sans-serif;box-shadow:var(--shadow-md);';
  host.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .3s'; setTimeout(() => el.remove(), 300); }, 2200);
}
