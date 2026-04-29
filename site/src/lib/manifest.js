/**
 * Loads the backend-curated artifact bundle and exposes lookup helpers.
 * Frontend's source of truth: site/public/data/app-manifest.json
 *
 * Resilience: every loader fails open. If a JSON is missing, returns a sane empty
 * shape so pages still render and surface a "data loading" chip.
 */

const DATA_BASE = '/data';

const _cache = new Map();

async function fetchJSON(path, fallback) {
  if (_cache.has(path)) return _cache.get(path);
  try {
    const res = await fetch(path, { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    _cache.set(path, data);
    return data;
  } catch (err) {
    console.warn(`[manifest] failed to load ${path}:`, err.message);
    _cache.set(path, fallback);
    return fallback;
  }
}

export async function loadManifest() {
  return fetchJSON(`${DATA_BASE}/app-manifest.json`, {
    generated_at: null,
    build_sha: null,
    artifacts: [],
    routes: [],
    _missing: true,
  });
}

export async function loadOverview() {
  return fetchJSON(`${DATA_BASE}/overview.json`, {
    position: [],
    headline_numbers: { rows_scanned: 0, findings: 0, dollars_today: 0, models_used: 0 },
    status_breakdown: { sql_executed: 0, schema_safe: 0, materialized: 0, external_needed: 0 },
    build_meta: { generated_at: null, build_sha: null, challenges_total: 11 },
    _missing: true,
  });
}

export async function loadChallenges() {
  return fetchJSON(`${DATA_BASE}/challenges.json`, []);
}

export async function loadChallenge(idOrSlug) {
  const all = await loadChallenges();
  return all.find(c => c.id === idOrSlug || c.slug === idOrSlug || c.number === Number(idOrSlug)) || null;
}

export async function loadFindingsIndex() {
  return fetchJSON(`${DATA_BASE}/findings-index.json`, []);
}

export async function loadAuditSummary() {
  return fetchJSON(`${DATA_BASE}/audit-summary.json`, {
    total: 0, clean: 0, needs_review: 0, unsafe: 0, per_challenge: [], _missing: true,
  });
}

export async function loadExecutionProof() {
  return fetchJSON(`${DATA_BASE}/execution-proof.json`, []);
}

export async function loadQAContext() {
  return fetchJSON(`${DATA_BASE}/qa-context.json`, {
    system_prompt: '',
    schema: {},
    story_packets: [],
    audit: {},
    top_findings: [],
    citations: [],
    _missing: true,
  });
}

export async function loadChartData(name) {
  return fetchJSON(`${DATA_BASE}/charts/${name}.json`, { _missing: true, data: [] });
}

/**
 * Returns true if the curated bundle is missing or empty.
 * Pages can use this to show a "data loading" banner.
 */
export async function isBundleReady() {
  const m = await loadManifest();
  return !m._missing && Array.isArray(m.artifacts) && m.artifacts.length > 0;
}

export async function manifestArtifact(id) {
  const m = await loadManifest();
  return (m.artifacts || []).find(a => a.id === id);
}
