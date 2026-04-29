/**
 * Top navigation. Renders into the first <nav class="nav"></nav> on the page.
 * Highlights the active section based on current pathname. Renders the review badge.
 */

import { bindNavBadge } from './decisions.js';

const LINKS = [
  { label: 'Cost',      path: '/index.html',     match: ['/', '/index.html'] },
  { label: 'Findings',  path: '/stories.html',   match: ['/stories.html'] },
  { label: 'Evidence',  path: '/trust.html',     match: ['/trust.html'] },
  { label: 'Sovereign AI',  path: '/sovereignty-dialogue.html', match: ['/sovereignty-dialogue.html'] },
  { label: 'Ask',      path: '/explore/ask.html', match: ['/explore/ask.html'] },
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
  if (current.startsWith('/challenges/') && link.label === 'Findings') return true;
  return false;
}

function linkAttrs(link, current) {
  const active = isActive(link, current);
  return {
    cls: active ? 'nav__link is-active' : 'nav__link',
    current: active ? ' aria-current="page"' : '',
  };
}

function bindScrollState(mount) {
  if (mount.dataset.scrollStateBound === 'true') return;
  mount.dataset.scrollStateBound = 'true';
  const update = () => {
    mount.classList.toggle('is-scrolled', window.scrollY > 12);
  };
  update();
  window.addEventListener('scroll', update, { passive: true });
}

export function renderNav() {
  const mount = document.querySelector('.nav');
  if (!mount) return;
  const current = pathnameNormalized();

  const links = LINKS.map(l => {
    const attrs = linkAttrs(l, current);
    return `<a class="${attrs.cls}" href="${l.path}"${attrs.current}>${l.label}</a>`;
  }).join('');

  const decisionsActive = current === '/explore/decisions.html';
  const decisionsClass = decisionsActive ? 'nav__link nav__link--decision is-active' : 'nav__link nav__link--decision';
  const decisionsCurrent = decisionsActive ? ' aria-current="page"' : '';

  mount.innerHTML = `
    <a class="nav__brand" href="/">Agency 2026<span class="dot">.</span> LemonClaw</a>
    <div class="nav__links">${links}</div>
    <div class="nav__actions">
      <a class="${decisionsClass}" href="/explore/decisions.html"${decisionsCurrent}>My decisions <span class="nav__badge is-zero" data-badge="reviews">0</span></a>
    </div>
  `;

  bindNavBadge('.nav__badge[data-badge="reviews"]');
  bindScrollState(mount);
}

if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNav);
  } else {
    renderNav();
  }
}
