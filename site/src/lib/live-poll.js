/**
 * Live polling for headline numbers + cost chart.
 *
 * Polls every 90 seconds while the clock is below the freeze deadline.
 * After freeze, stops polling and surfaces a "FROZEN" badge across the page.
 *
 * The freeze is the submission cutoff: 2026-04-29 14:00 America/Toronto.
 * That is 2026-04-29T18:00:00Z UTC.
 */

import { fmtUSD, fmtInt } from './data-format.js';
import { renderCostOverTime, renderHHI } from './charts.js';

const FREEZE_AT_UTC = '2026-04-29T18:00:00Z';
const POLL_INTERVAL_MS = 60 * 1000;

let _timer = null;
let _frozen = false;
let _startedAt = Date.now();
let _onCount = 0;

function isFrozen() {
  if (_frozen) return true;
  const now = Date.now();
  if (now >= Date.parse(FREEZE_AT_UTC)) {
    _frozen = true;
    return true;
  }
  return false;
}

function timeUntilFreeze() {
  return Math.max(0, Date.parse(FREEZE_AT_UTC) - Date.now());
}

function fmtCountdown(ms) {
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, '0')}m`;
  return `${m}m ${String(s).padStart(2, '0')}s`;
}

function renderBadge() {
  let badge = document.getElementById('lc-live-badge');
  if (!badge) {
    badge = document.createElement('div');
    badge.id = 'lc-live-badge';
    badge.style.cssText = `
      position: fixed; top: 12px; right: 12px; z-index: 100;
      padding: 6px 12px; border-radius: 999px;
      font-family: "JetBrains Mono", monospace; font-size: 11px;
      letter-spacing: 0.06em; text-transform: uppercase;
      background: var(--paper); border: 1px solid var(--orange-border); color: var(--orange-deep);
      box-shadow: var(--shadow-sm);
    `;
    document.body.appendChild(badge);
  }
  if (isFrozen()) {
    badge.style.background = 'var(--ink)';
    badge.style.color = 'var(--paper)';
    badge.style.borderColor = 'var(--ink)';
    badge.innerHTML = `<span style="display:inline-block; width: 6px; height: 6px; border-radius: 50%; background: hsl(0, 62%, 60%); margin-right: 8px;"></span>Submission frozen · 14:00 ET`;
  } else {
    badge.style.background = 'var(--paper)';
    badge.style.color = 'var(--orange-deep)';
    badge.style.borderColor = 'var(--orange-border)';
    badge.innerHTML = `<span style="display:inline-block; width: 6px; height: 6px; border-radius: 50%; background: var(--green); margin-right: 8px; animation: pulse 1.5s ease-in-out infinite;"></span>Live · freezes in ${fmtCountdown(timeUntilFreeze())}`;
  }
}

// Inject pulse keyframe once
function ensurePulseStyle() {
  if (document.getElementById('lc-pulse-style')) return;
  const style = document.createElement('style');
  style.id = 'lc-pulse-style';
  style.textContent = `@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }`;
  document.head.appendChild(style);
}

async function pullLatestOverview() {
  // Add a cache-buster so we always see the latest overview.json
  const url = `/data/overview.json?t=${Date.now()}`;
  try {
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

async function refreshNumbers() {
  const ov = await pullLatestOverview();
  if (!ov) return;

  const n = ov.headline_numbers || {};
  const sov = ov.sovereignty || {};
  const map = {
    'm-rows': fmtInt(n.rows_scanned),
    'm-findings': fmtInt(n.findings),
    'm-dollars': fmtUSD(n.dollars_today),
    'cost-headline': n.dollars_today != null ? `${fmtUSD(n.dollars_today)} today.` : null,
    'sov-headline': n.dollars_today != null ? `${fmtUSD(n.dollars_today)} today.` : null,
    // Per-provider breakdown from sovereignty tracker
    'c-claude': sov.claude_cost_usd != null ? fmtUSD(sov.claude_cost_usd) : null,
    'c-codex': sov.codex_cost_usd != null ? fmtUSD(sov.codex_cost_usd) : null,
    'c-openrouter': sov.openrouter_cost_usd != null ? fmtUSD(sov.openrouter_cost_usd) : null,
  };
  for (const [id, val] of Object.entries(map)) {
    const el = document.getElementById(id);
    if (el && val != null) {
      const previous = el.textContent;
      el.textContent = val;
      if (previous !== val) flashEl(el);
    }
  }

  // Status strip is derived from challenges.json, not overview.status_breakdown.
  // Refresh it from the live challenge bundle.
  try {
    const chRes = await fetch(`/data/challenges.json?t=${Date.now()}`, { cache: 'no-store' });
    if (chRes.ok) {
      const challenges = await chRes.json();
      const counts = { 'sql-executed': 0, materialized: 0, 'external-needed': 0, 'schema-safe': 0 };
      for (const c of challenges) {
        for (const lv of (c.proof_levels || [])) {
          if (lv in counts) counts[lv]++;
        }
      }
      const sMap = {
        's-sql': counts['sql-executed'],
        's-mat': counts.materialized,
        's-ext': counts['external-needed'],
        's-safe': counts['schema-safe'],
      };
      for (const [id, val] of Object.entries(sMap)) {
        const el = document.getElementById(id);
        if (el) el.textContent = fmtInt(val);
      }
    }
  } catch { /* keep prior */ }
}

async function refreshCostChart() {
  const canvas = document.getElementById('chart-cost');
  if (!canvas) return;
  // Tear down + redraw. Chart.js stores instance on the canvas; destroy if present.
  try {
    const inst = (await import('chart.js')).Chart.getChart(canvas);
    if (inst) inst.destroy();
  } catch { /* ignore */ }
  await renderCostOverTime(canvas, document.getElementById('cap-cost'));
}

async function refreshHHIChart() {
  const canvas = document.getElementById('chart-hhi');
  if (!canvas) return;
  try {
    const inst = (await import('chart.js')).Chart.getChart(canvas);
    if (inst) inst.destroy();
  } catch { /* ignore */ }
  await renderHHI(canvas, document.getElementById('cap-hhi'));
}

function flashEl(el) {
  el.style.transition = 'background-color 0.4s ease';
  const orig = el.style.backgroundColor;
  el.style.backgroundColor = 'hsl(28, 79%, 90%)';
  setTimeout(() => { el.style.backgroundColor = orig; }, 600);
}

export function startLivePoll(opts = {}) {
  ensurePulseStyle();
  renderBadge();

  if (isFrozen()) {
    return { frozen: true, cleanup: () => {} };
  }

  const tick = async () => {
    _onCount++;
    renderBadge();
    if (isFrozen()) {
      stopLivePoll();
      return;
    }
    await refreshNumbers();
    if (opts.includeCostChart !== false) await refreshCostChart();
    // HHI chart on home is an artifact of the loop set, less time-sensitive; refresh every 5th tick
    if (_onCount % 5 === 0 && opts.includeHHIChart !== false) await refreshHHIChart();
  };

  // Poll a countdown every second so the badge stays accurate
  const badgeTick = setInterval(() => { renderBadge(); if (isFrozen()) { clearInterval(badgeTick); stopLivePoll(); } }, 1000);

  _timer = setInterval(tick, POLL_INTERVAL_MS);

  return {
    frozen: false,
    cleanup: () => {
      if (_timer) { clearInterval(_timer); _timer = null; }
      clearInterval(badgeTick);
    },
  };
}

export function stopLivePoll() {
  if (_timer) { clearInterval(_timer); _timer = null; }
  _frozen = true;
  renderBadge();
}

export const FREEZE = { at: FREEZE_AT_UTC, isFrozen, timeUntilFreeze };
