/**
 * Top navigation. Renders into the first <nav class="nav"></nav> on the page.
 * Highlights the active section based on current pathname. Renders the review badge.
 */

import { bindNavBadge } from './decisions.js';

const LINKS = [
  { label: 'Home',           path: '/index.html',          match: ['/', '/index.html'] },
  { label: 'The eleven loops', path: '/index.html#loops',  match: [], anchor: true },
  { label: 'Cost',            path: '/explore/sovereignty.html', match: ['/explore/sovereignty.html'] },
  { label: 'Audit',           path: '/explore/audit.html',  match: ['/explore/audit.html'] },
  { label: 'Stories',         path: '/explore/stories.html', match: ['/explore/stories.html'] },
  { label: 'Ask',             path: '/explore/ask.html',    match: ['/explore/ask.html'] },
];

function pathnameNormalized() {
  let p = window.location.pathname || '/';
  // Treat '' / '/' / '/index.html' as same
  if (p === '' || p === '/') p = '/index.html';
  return p;
}

function isActive(link, current) {
  if (link.anchor) return false;
  if (link.match.includes(current)) return true;
  if (current.startsWith('/challenges/') && link.label === 'The eleven loops') return true;
  return false;
}

export function renderNav() {
  const mount = document.querySelector('.nav');
  if (!mount) return;
  const current = pathnameNormalized();

  const links = LINKS.map(l => {
    const cls = isActive(l, current) ? 'nav__link is-active' : 'nav__link';
    return `<a class="${cls}" href="${l.path}">${l.label}</a>`;
  }).join('');

  mount.innerHTML = `
    <a class="nav__brand" href="/">Agency 2026<span class="dot">.</span> LemonClaw</a>
    <div class="nav__links">${links}</div>
    <a class="nav__link" href="/explore/decisions.html">My review <span class="nav__badge is-zero" data-badge="reviews">0</span></a>
  `;

  bindNavBadge('.nav__badge[data-badge="reviews"]');
}

if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNav);
  } else {
    renderNav();
  }
}
