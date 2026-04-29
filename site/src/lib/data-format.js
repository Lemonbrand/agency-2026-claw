/**
 * Display helpers used across pages.
 */

export function escText(s) {
  return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
export function escAttr(s) {
  return String(s ?? '').replace(/"/g, '&quot;');
}

export function fmtUSD(n, digits = 2) {
  if (n == null || isNaN(n)) return '—';
  if (n < 0.01 && n > 0) return '$' + n.toFixed(4);
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtInt(n) {
  if (n == null || isNaN(n)) return '—';
  return Number(n).toLocaleString('en-US');
}

export function fmtPct(n, digits = 1) {
  if (n == null || isNaN(n)) return '—';
  return (Number(n) * 100).toFixed(digits) + '%';
}

export function shortHash(s, n = 7) {
  if (!s) return '';
  return String(s).slice(0, n);
}

export function relativeTime(iso) {
  if (!iso) return '';
  const now = Date.now();
  const t = new Date(iso).getTime();
  if (isNaN(t)) return '';
  const diff = Math.max(0, now - t);
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}
