/*
 * Guided tour. One spotlight, one tooltip, sequential steps.
 * Auto-fires once on home (localStorage flag). Replay via bindTourTrigger().
 *
 * Usage:
 *   import { startTour, bindTourTrigger, autoStartIfFirstVisit } from './tour.js';
 *   const STEPS = [{ selector: '.foo', title: '...', body: '...' }, ...];
 *   autoStartIfFirstVisit(STEPS);
 *   bindTourTrigger('#replay-tour-btn', STEPS);
 */

const SEEN_KEY = 'lc_tour_seen_v1';

let _backdrop, _spot, _tip, _idx = 0, _steps = [], _onCloseCb = null;
let _resizeBound = false;
let _onKeyHandler = null;
let _initialScrollY = 0;

function ensureMounted() {
  if (_backdrop) return;
  _backdrop = document.createElement('div');
  _backdrop.className = 'tour-backdrop';
  _backdrop.addEventListener('click', endTour);

  _spot = document.createElement('div');
  _spot.className = 'tour-spot';
  _spot.setAttribute('aria-hidden', 'true');

  _tip = document.createElement('div');
  _tip.className = 'tour-tip';
  _tip.setAttribute('role', 'dialog');
  _tip.setAttribute('aria-live', 'polite');

  document.body.appendChild(_backdrop);
  document.body.appendChild(_spot);
  document.body.appendChild(_tip);

  if (!_resizeBound) {
    window.addEventListener('resize', () => { if (_steps.length) place(); }, { passive: true });
    window.addEventListener('scroll', () => { if (_steps.length) place(); }, { passive: true });
    _resizeBound = true;
  }
}

function el(sel) {
  return typeof sel === 'string' ? document.querySelector(sel) : sel;
}

function rectOf(target) {
  const r = target.getBoundingClientRect();
  // Pad a touch so the spotlight breathes around the element
  const pad = 8;
  return {
    top: r.top - pad,
    left: r.left - pad,
    width: r.width + pad * 2,
    height: r.height + pad * 2,
  };
}

function place() {
  const step = _steps[_idx];
  if (!step) return;
  const target = el(step.selector);
  if (!target) {
    // Element missing — skip gracefully
    next();
    return;
  }
  // Bring the target into view if it's off-screen.
  // Use behavior: 'auto' (instant) so there's no lingering smooth-scroll
  // animation if the user ends the tour mid-scroll.
  const tr = target.getBoundingClientRect();
  const vh = window.innerHeight;
  if (tr.top < 60 || tr.bottom > vh - 60) {
    target.scrollIntoView({ behavior: 'auto', block: 'center' });
  }

  const r = rectOf(target);
  Object.assign(_spot.style, {
    top: `${r.top}px`,
    left: `${r.left}px`,
    width: `${r.width}px`,
    height: `${r.height}px`,
  });

  // Position the tip below the spot if there's room, otherwise above, else center.
  const tipH = _tip.offsetHeight || 220;
  const tipW = _tip.offsetWidth || 360;
  const margin = 16;
  let top = r.top + r.height + margin;
  let left = r.left + r.width / 2 - tipW / 2;

  // Flip above if not enough room below
  if (top + tipH > window.innerHeight - 16) {
    top = r.top - tipH - margin;
  }
  // Center vertically if no room above either
  if (top < 16) {
    top = Math.max(16, (window.innerHeight - tipH) / 2);
  }
  // Keep tip on-screen horizontally
  left = Math.max(16, Math.min(window.innerWidth - tipW - 16, left));

  Object.assign(_tip.style, { top: `${top}px`, left: `${left}px` });
}

function paint() {
  const step = _steps[_idx];
  const isLast = _idx === _steps.length - 1;
  _tip.innerHTML = `
    <div class="tour-tip__step">Step ${_idx + 1} of ${_steps.length}</div>
    <div class="tour-tip__title">${step.title || ''}</div>
    <div class="tour-tip__body">${step.body || ''}</div>
    <div class="tour-tip__row">
      <button class="btn btn--small" data-act="skip">Skip tour</button>
      <span class="spacer"></span>
      ${_idx > 0 ? `<button class="btn btn--small" data-act="back">Back</button>` : ''}
      <button class="btn btn--primary btn--small" data-act="next">${isLast ? 'Done' : 'Next'}</button>
    </div>
  `;
  _tip.querySelector('[data-act="skip"]').addEventListener('click', endTour);
  _tip.querySelector('[data-act="next"]').addEventListener('click', next);
  const backBtn = _tip.querySelector('[data-act="back"]');
  if (backBtn) backBtn.addEventListener('click', back);
  place();
  _tip.querySelector('[data-act="next"]').focus();
}

function next() {
  if (_idx >= _steps.length - 1) { endTour(); return; }
  _idx += 1;
  paint();
}
function back() {
  if (_idx === 0) return;
  _idx -= 1;
  paint();
}

export function startTour(steps, opts = {}) {
  _steps = (steps || []).filter(s => s && s.selector && document.querySelector(s.selector));
  if (!_steps.length) return false;
  _idx = 0;
  _onCloseCb = opts.onClose || null;
  _initialScrollY = window.scrollY;
  ensureMounted();
  _backdrop.classList.add('is-on');
  _spot.classList.add('is-on');
  _tip.classList.add('is-on');
  document.documentElement.classList.add('tour-active');

  _onKeyHandler = e => {
    if (e.key === 'Escape') endTour();
    else if (e.key === 'ArrowRight' || e.key === 'Enter') next();
    else if (e.key === 'ArrowLeft') back();
  };
  document.addEventListener('keydown', _onKeyHandler);

  paint();
  return true;
}

export function endTour() {
  if (!_backdrop) return;
  _backdrop.classList.remove('is-on');
  _spot.classList.remove('is-on');
  _tip.classList.remove('is-on');
  document.documentElement.classList.remove('tour-active');
  if (_onKeyHandler) {
    document.removeEventListener('keydown', _onKeyHandler);
    _onKeyHandler = null;
  }
  // Restore the user's original scroll position instantly so the tour does
  // not leave them somewhere they didn't choose.
  window.scrollTo({ top: _initialScrollY, behavior: 'auto' });
  try { localStorage.setItem(SEEN_KEY, '1'); } catch {}
  if (_onCloseCb) _onCloseCb();
}

export function bindTourTrigger(selector, steps) {
  const btn = typeof selector === 'string' ? document.querySelector(selector) : selector;
  if (!btn) return;
  btn.addEventListener('click', e => {
    e.preventDefault();
    try { localStorage.removeItem(SEEN_KEY); } catch {}
    startTour(steps);
  });
}

export function autoStartIfFirstVisit(steps, delayMs = 500) {
  let seen = false;
  try { seen = localStorage.getItem(SEEN_KEY) === '1'; } catch {}
  if (seen) return;
  // Wait for layout + any post-load paints
  setTimeout(() => startTour(steps), delayMs);
}
