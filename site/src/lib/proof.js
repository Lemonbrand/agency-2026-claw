/**
 * Evidence-status chip taxonomy. Internal keys stay stable because the backend
 * contract uses them, but the labels are written for policy and program teams.
 */

const PROOF_LABELS = {
  'schema-safe':     { label: 'Data fields verified', tooltip: 'The source fields named by this check exist in the supplied data.' },
  'sql-executed':    { label: 'Query ran',            tooltip: 'A read-only query ran against the GovAlta database. Row count, runtime, and query hash were captured.' },
  'materialized':    { label: 'Needs prepared data',  tooltip: 'The check can proceed, but it needs a prepared subset, computed field, or follow-up join before promotion.' },
  'external-needed': { label: 'Needs outside source', tooltip: 'The supplied database does not contain enough evidence. The missing outside source is named.' },
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
    case 'runnable':     return 'Ready to review';
    case 'materialized': return 'Needs prepared data';
    case 'external':     return 'Needs outside source';
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
