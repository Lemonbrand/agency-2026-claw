/**
 * Proof-level chip taxonomy. Distinguishes lexical-audit cleanliness from execution proof.
 *
 * - schema-safe: lexical audit clean, references resolve.
 * - sql-executed: probe SQL ran end-to-end; row count + runtime captured.
 * - materialized: needs subset preparation or computed column.
 * - external-needed: requires data outside the GovAlta bundle.
 *
 * A challenge can carry multiple chips (e.g. schema-safe + sql-executed).
 */

const PROOF_LABELS = {
  'schema-safe':     { label: 'Schema safe',     tooltip: 'Lexical audit clean. Every table and column reference resolves to the verified schema.' },
  'sql-executed':    { label: 'SQL executed',    tooltip: 'A probe query ran end-to-end against the GovAlta database. Row count, runtime, and SQL hash captured.' },
  'materialized':    { label: 'Materialized',    tooltip: 'Needs subset preparation or one computed column before it runs.' },
  'external-needed': { label: 'External needed', tooltip: 'Requires data not in the GovAlta bundle. The brief names the source.' },
};

export function renderProofChips(levels = []) {
  if (!Array.isArray(levels) || levels.length === 0) {
    return `<span class="chip gray" title="No proof level reported yet">unclassified</span>`;
  }
  return levels.map(level => {
    const meta = PROOF_LABELS[level] || { label: level, tooltip: '' };
    return `<span class="chip proof-${level}" title="${escapeAttr(meta.tooltip)}">${escapeText(meta.label)}</span>`;
  }).join('');
}

export function statusToChipClass(status) {
  switch ((status || '').toLowerCase()) {
    case 'runnable':   return 'green';
    case 'materialized': return 'amber';
    case 'external':   return 'gray';
    case 'refused':    return 'gray';
    default:           return 'gray';
  }
}

export function statusLabel(status) {
  switch ((status || '').toLowerCase()) {
    case 'runnable':     return 'Runnable now';
    case 'materialized': return 'Needs materialization';
    case 'external':     return 'Needs external data';
    case 'refused':      return 'Refused';
    default:             return status || 'unclassified';
  }
}

function escapeText(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function escapeAttr(s) {
  return String(s ?? '').replace(/"/g, '&quot;');
}
