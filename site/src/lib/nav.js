/**
 * Top navigation. Renders into the first <nav class="nav"></nav> on the page.
 * Highlights the active section based on current pathname. Renders the review badge.
 */

import { bindNavBadge } from './decisions.js';

const AWARD_POPUP_KEY = 'lc_award_popup_dismissed_v1';

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

function renderAwardBanner(mount) {
  if (document.querySelector('.award-banner')) return;
  const banner = document.createElement('section');
  banner.className = 'award-banner';
  banner.setAttribute('aria-label', 'Agency 2026 award note');
  banner.innerHTML = `
    <div class="award-banner__eyebrow">Agency 2026 Ottawa</div>
    <div class="award-banner__copy">
      <strong>This project won first place.</strong>
      Thank you to the <a href="https://luma.com/5e83iia8" target="_blank" rel="noopener">Government of Alberta</a> for making the event happen, and to the organizers, sponsors, judges, and participants who pushed the work.
    </div>
    <div class="award-banner__links">
      <a href="https://github.com/GovAlta/agency-26-hackathon" target="_blank" rel="noopener">GovAlta repo</a>
      <a href="https://lemonbrand.io" target="_blank" rel="noopener">Lemonbrand</a>
    </div>
  `;
  mount.insertAdjacentElement('afterend', banner);
}

function renderAwardPopup() {
  if (localStorage.getItem(AWARD_POPUP_KEY) === '1') return;
  if (document.querySelector('.award-popup')) return;
  const popup = document.createElement('aside');
  popup.className = 'award-popup';
  popup.setAttribute('aria-label', 'First place thank you note');
  popup.innerHTML = `
    <button class="award-popup__close" type="button" aria-label="Dismiss first place note">×</button>
    <img class="award-popup__icon" src="/img/3dicons/heart.png" alt="" aria-hidden="true">
    <div class="award-popup__body">
      <div class="award-popup__eyebrow">Agency 2026 Ottawa</div>
      <strong>This project won first place.</strong>
      <p>Built in a day to show accountable AI for public data: find patterns, refuse weak claims, and leave receipts.</p>
      <div class="award-popup__actions">
        <a class="btn btn--primary btn--small" href="https://cal.com/lemonbrand/coffee" target="_blank" rel="noopener">Coffee with Simon</a>
        <a class="btn btn--ghost btn--small" href="https://lemonbrand.io" target="_blank" rel="noopener">View Lemonbrand</a>
      </div>
    </div>
  `;
  popup.querySelector('.award-popup__close')?.addEventListener('click', () => {
    localStorage.setItem(AWARD_POPUP_KEY, '1');
    popup.remove();
  });
  document.body.appendChild(popup);
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
  renderAwardBanner(mount);
  renderAwardPopup();
}

if (typeof window !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderNav);
  } else {
    renderNav();
  }
}
