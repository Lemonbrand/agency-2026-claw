/**
 * Judge decisions: localStorage CRUD + JSON export + print-friendly summary.
 * Storage key: lc_decisions_v1.
 *
 * Each decision is one of: promote | review | reject. Optional note. Persists
 * across page reloads. Powers the top-nav badge counter.
 */

const KEY = 'lc_decisions_v1';

function uuid() {
  if (typeof crypto?.randomUUID === 'function') return crypto.randomUUID();
  return 'sess-' + Math.random().toString(36).slice(2, 10) + '-' + Date.now().toString(36);
}

function nowIso() { return new Date().toISOString(); }

export function loadStore() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* fall through */ }
  return initStore();
}

function initStore() {
  const store = {
    session_id: uuid(),
    started_at: nowIso(),
    judge_email: null,
    judge_name: null,
    decisions: {},
    questions_asked: [],
  };
  saveStore(store);
  return store;
}

function saveStore(store) {
  try { localStorage.setItem(KEY, JSON.stringify(store)); }
  catch (err) { console.warn('[decisions] failed to save:', err.message); }
}

export function setDecision(challengeId, verdict, note) {
  const store = loadStore();
  store.decisions[challengeId] = {
    verdict,
    note: note || '',
    decided_at: nowIso(),
  };
  saveStore(store);
  emitChange(store);
  return store.decisions[challengeId];
}

export function getDecision(challengeId) {
  const store = loadStore();
  return store.decisions[challengeId] || null;
}

export function clearDecision(challengeId) {
  const store = loadStore();
  delete store.decisions[challengeId];
  saveStore(store);
  emitChange(store);
}

export function setJudge(name, email) {
  const store = loadStore();
  if (name !== undefined) store.judge_name = name;
  if (email !== undefined) store.judge_email = email;
  saveStore(store);
  emitChange(store);
}

export function logQuestion(model, question, answerSnippet, costUsd, tokens) {
  const store = loadStore();
  store.questions_asked.push({
    ts: nowIso(),
    model,
    question,
    answer_snippet: (answerSnippet || '').slice(0, 240),
    cost_usd: Number(costUsd || 0),
    tokens_in: tokens?.in ?? null,
    tokens_out: tokens?.out ?? null,
  });
  if (store.questions_asked.length > 100) {
    store.questions_asked = store.questions_asked.slice(-100);
  }
  saveStore(store);
  emitChange(store);
}

export function summary() {
  const store = loadStore();
  const decisions = Object.values(store.decisions);
  return {
    total: decisions.length,
    promote: decisions.filter(d => d.verdict === 'promote').length,
    review:  decisions.filter(d => d.verdict === 'review').length,
    reject:  decisions.filter(d => d.verdict === 'reject').length,
    questions_asked: store.questions_asked.length,
    total_qa_cost_usd: store.questions_asked.reduce((s, q) => s + (q.cost_usd || 0), 0),
    started_at: store.started_at,
    judge: { name: store.judge_name, email: store.judge_email },
  };
}

export function exportJson() {
  const store = loadStore();
  const blob = new Blob([JSON.stringify(store, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  const date = nowIso().slice(0, 10);
  const judge = (store.judge_name || 'judge').toLowerCase().replace(/\W+/g, '-');
  a.href = url;
  a.download = `agency2026-decisions-${judge}-${date}.json`;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 100);
}

export function emitChange(store = null) {
  const data = store || loadStore();
  document.dispatchEvent(new CustomEvent('lc:decisions-changed', { detail: summary() }));
  return data;
}

/** Initialize a global change listener so the nav badge stays in sync. */
export function bindNavBadge(selector = '.nav__badge[data-badge="reviews"]') {
  const update = () => {
    const el = document.querySelector(selector);
    if (!el) return;
    const s = summary();
    el.textContent = String(s.total);
    el.classList.toggle('is-zero', s.total === 0);
  };
  update();
  document.addEventListener('lc:decisions-changed', update);
  window.addEventListener('storage', e => { if (e.key === KEY) update(); });
}
