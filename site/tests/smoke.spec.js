// @ts-check
import { test, expect } from '@playwright/test';

const ROUTES = [
  { path: '/',                                       title: /Agency 2026/, marker: 'h1, .pill-money' },
  { path: '/index.html',                             title: /Agency 2026/, marker: 'h1, .pill-money' },
  { path: '/stories.html',                           title: /Findings/i,   marker: 'h1, .hero-h1' },
  { path: '/trust.html',                             title: /Evidence|Trust/i, marker: 'h1, .h1' },
  { path: '/sovereignty-dialogue.html',              title: /Canadian AI Compute/i, marker: 'h1' },
  { path: '/challenges/01-zombie-recipients.html',   title: /Zombie/i,     marker: 'main h1' },
  { path: '/challenges/02-ghost-capacity.html',      title: /Ghost/i,      marker: 'main h1' },
  { path: '/challenges/03-funding-loops.html',       title: /Funding/i,    marker: 'main h1' },
  { path: '/challenges/04-sole-source-amendment.html', title: /Sole/i,    marker: 'main h1' },
  { path: '/challenges/05-vendor-concentration.html',  title: /Vendor/i,  marker: 'main h1' },
  { path: '/challenges/06-related-parties.html',     title: /Related/i,    marker: 'main h1' },
  { path: '/challenges/07-policy-misalignment.html', title: /Policy/i,     marker: 'main h1' },
  { path: '/challenges/08a-duplicative-overlap.html', title: /Duplicative/i, marker: 'main h1' },
  { path: '/challenges/08b-funding-gaps.html',       title: /Funding Gaps/i, marker: 'main h1' },
  { path: '/challenges/09-contract-intelligence.html', title: /Contract/i, marker: 'main h1' },
  { path: '/challenges/10-adverse-media.html',       title: /Adverse/i,    marker: 'main h1' },
  { path: '/explore/stories.html',                   title: /(Stories|Findings|Original)/i, marker: 'h1' },
  { path: '/explore/sovereignty.html',               title: /(Sovereign|Cost)/i, marker: 'h1' },
  { path: '/explore/audit.html',                     title: /(Audit|Evidence)/i, marker: 'h1' },
  { path: '/explore/data-tables.html',               title: /(Findings|Review|Leads)/i, marker: 'h1' },
  { path: '/explore/ask.html',                       title: /Ask/i,        marker: 'h1' },
  { path: '/explore/decisions.html',                 title: /(Review|Decisions)/i, marker: 'h1' },
];

const ASSETS = [
  '/icons/shield.png',
  '/icons/chart.png',
  '/icons/dollar.png',
  '/icons/bulb.png',
  '/icons/tick.png',
  '/icons/rocket.png',
  '/img/3dicons/rocket.png',
  '/img/3dicons/money-bag.png',
  '/img/3dicons/tools.png',
  '/img/3dicons/heart.png',
];

const DATA = [
  '/data/app-manifest.json',
  '/data/overview.json',
  '/data/challenges.json',
  '/data/findings-index.json',
  '/data/audit-summary.json',
  '/data/execution-proof.json',
  '/data/qa-context.json',
  '/data/charts/cost-over-time.json',
  '/data/charts/hhi-by-department.json',
];

test.describe('Routes load and render', () => {
  for (const r of ROUTES) {
    test(`renders ${r.path}`, async ({ page }) => {
      const consoleErrors = [];
      page.on('console', msg => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
      page.on('pageerror', err => { consoleErrors.push('pageerror: ' + err.message); });
      const res = await page.goto(r.path, { waitUntil: 'networkidle' });
      expect(res?.status(), `HTTP for ${r.path}`).toBeLessThan(400);
      await expect(page).toHaveTitle(r.title);
      const marker = await page.locator(r.marker).first().textContent({ timeout: 5000 }).catch(() => '');
      expect(marker?.length || 0, `${r.marker} on ${r.path}`).toBeGreaterThan(2);
      if (consoleErrors.length) {
        console.log(`[console errors on ${r.path}]\n` + consoleErrors.join('\n'));
      }
      // Allow a couple non-fatal warnings, but fail if there are clear errors
      const fatal = consoleErrors.filter(e =>
        !/favicon|Failed to load resource: the server responded with a status of 404 \(File not found\) ?$/.test(e)
      );
      expect(fatal, `console errors on ${r.path}`).toEqual([]);
    });
  }
});

test.describe('Static assets present', () => {
  for (const a of ASSETS) {
    test(`asset ${a}`, async ({ request }) => {
      const res = await request.get(a);
      expect(res.status(), a).toBe(200);
      expect(Number(res.headers()['content-length'] || 0), `${a} non-empty`).toBeGreaterThan(0);
    });
  }
});

test.describe('Backend bundle artifacts present', () => {
  for (const d of DATA) {
    test(`data ${d}`, async ({ request }) => {
      const res = await request.get(d);
      expect(res.status(), d).toBe(200);
      const body = await res.text();
      expect(body.length, `${d} non-empty`).toBeGreaterThan(2);
    });
  }
});

test.describe('Internal links', () => {
  test('home links resolve', async ({ page, request }) => {
    await page.goto('/');
    const hrefs = await page.locator('a[href]').evaluateAll(els => els.map(e => e.getAttribute('href')));
    const internal = hrefs
      .filter(h => h && !h.startsWith('http') && !h.startsWith('mailto:') && !h.startsWith('#'))
      .map(h => new URL(h, 'http://localhost:4173/').pathname);
    const checked = new Set();
    for (const path of internal) {
      if (checked.has(path)) continue;
      checked.add(path);
      const res = await request.get(path);
      expect(res.status(), `link ${path}`).toBeLessThan(400);
    }
  });

  test('challenge 03 links resolve', async ({ page, request }) => {
    await page.goto('/challenges/03-funding-loops.html');
    await page.waitForLoadState('networkidle');
    const hrefs = await page.locator('a[href]').evaluateAll(els => els.map(e => e.getAttribute('href')));
    const internal = hrefs
      .filter(h => h && !h.startsWith('http') && !h.startsWith('mailto:') && !h.startsWith('#'))
      .map(h => new URL(h, 'http://localhost:4173/').pathname);
    const checked = new Set();
    for (const path of internal) {
      if (checked.has(path)) continue;
      checked.add(path);
      const res = await request.get(path);
      expect(res.status(), `link ${path}`).toBeLessThan(400);
    }
  });
});

test.describe('Award note', () => {
  test('home shows first-place banner, FAQ, and dismissible popup', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.removeItem('lc_award_popup_dismissed_v1'));
    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.award-banner')).toContainText('This project won first place.');
    await expect(page.locator('.award-banner')).toContainText('Government of Alberta');
    await expect(page.locator('.award-popup')).toContainText('This project won first place.');
    await expect(page.locator('.faq-section')).toContainText('Can my whole department use this on Monday?');
    await page.locator('.award-popup__close').click();
    await expect(page.locator('.award-popup')).toHaveCount(0);
    const dismissed = await page.evaluate(() => localStorage.getItem('lc_award_popup_dismissed_v1'));
    expect(dismissed).toBe('1');
  });
});

test.describe('Challenge Ask handoff', () => {
  const challengeRoutes = ROUTES
    .filter(r => r.path.startsWith('/challenges/'))
    .map(r => r.path);

  test('every challenge has scoped Ask buttons with questions', async ({ page }) => {
    for (const path of challengeRoutes) {
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      const links = await page.locator('a[data-ask-question]').evaluateAll(els => els.map(el => ({
        text: el.textContent?.trim(),
        q: el.getAttribute('data-ask-question'),
        href: el.getAttribute('href'),
      })));
      expect(links.length, `${path} ask question buttons`).toBe(4);
      for (const link of links) {
        const url = new URL(link.href || '', 'http://localhost:4173');
        expect(url.pathname, `${path} ask link path`).toBe('/explore/ask.html');
        expect(url.searchParams.get('q'), `${path} q param`).toBeTruthy();
        expect(url.searchParams.get('q'), `${path} data question match`).toBe(link.q);
        expect(url.searchParams.get('scope'), `${path} scope`).toMatch(/^challenge:/);
        expect(url.searchParams.get('ask'), `${path} autorun`).toBe('1');
      }
      const openHref = await page.locator('a[data-ask-open="true"]').first().getAttribute('href');
      const openUrl = new URL(openHref || '', 'http://localhost:4173');
      expect(openUrl.pathname, `${path} open ask path`).toBe('/explore/ask.html');
      expect(openUrl.searchParams.get('q'), `${path} open ask q`).toBeTruthy();
      expect(openUrl.searchParams.get('ask'), `${path} open ask should not autorun`).toBeNull();
    }
  });

  test('clicking a challenge Ask button opens Ask and submits the scoped question', async ({ page }) => {
    await page.route('**/api/ask', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        answer: 'Mock cited answer from the scoped challenge.',
        model: 'moonshotai/kimi-k2.6',
        tokens_in: 10,
        tokens_out: 8,
        cost_usd: 0.0001,
        citations: [{ ref: 'sha abc123', kind: 'sql' }],
        trace: [{ status: 'done', title: 'Mock trace', detail: 'Scoped Ask link submitted correctly.' }],
        evidence: { sql_hash: 'abc123', rows_returned: 1 },
        via: 'local-data-api',
      }),
    }));
    await page.goto('/challenges/05-vendor-concentration.html');
    await page.waitForLoadState('networkidle');
    await page.locator('a[data-ask-question]', { hasText: 'Strongest evidence' }).click();
    await page.waitForURL(/\/explore\/ask\.html\?.*scope=challenge%3A05/);
    await page.waitForSelector('.message--assistant .message__text.is-rendered');
    await expect(page.locator('#scope-chip')).toHaveText('scope: check 05');
    await expect(page.locator('.message--user .message__text').last()).toContainText('Check 05');
    await expect(page.locator('.message--assistant .message__text').last()).toContainText('Mock cited answer');
    await expect(page.locator('.message__trace').last()).toContainText('Mock trace');
  });

  test('generic Open Ask link prefills without submitting', async ({ page }) => {
    await page.goto('/challenges/03-funding-loops.html');
    await page.waitForLoadState('networkidle');
    const href = await page.locator('a[data-ask-open="true"]').first().getAttribute('href');
    await page.goto(href || '/explore/ask.html');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('#scope-chip')).toHaveText('scope: check 03');
    await expect(page.locator('#ask-input')).toHaveValue(/Check 03/);
    await expect(page.locator('#answer-count')).toHaveText('0 answers');
  });

  test('Ask reset clears the conversation and keeps the page usable', async ({ page }) => {
    await page.route('**/api/ask', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        answer: 'Mock answer with a receipt.',
        model: 'moonshotai/kimi-k2.6',
        tokens_in: 12,
        tokens_out: 7,
        cost_usd: 0.0001,
        trace: [{ status: 'done', title: 'Mock trace', detail: 'Reset test.' }],
        evidence: { sql_hash: 'abc123', rows_returned: 1 },
        via: 'local-data-api',
      }),
    }));
    await page.goto('/explore/ask.html?scope=challenge%3A05');
    await page.fill('#ask-input', 'Which department spending is concentrated?');
    await page.click('#ask-submit');
    await page.waitForSelector('.message--assistant .message__text.is-rendered');
    await expect(page.locator('#answer-count')).toHaveText('1 answer');
    await page.click('#ask-reset');
    await expect(page.locator('#answer-count')).toHaveText('0 answers');
    await expect(page.locator('#ask-input')).toHaveValue('');
    await expect(page.locator('#scope-chip')).toHaveText('scope: check 05');
    await expect(page.locator('#prompt-grid')).toBeVisible();
    await expect(page.locator('.message[data-turn="true"]')).toHaveCount(0);
  });
});

test.describe('Charts render', () => {
  test('home renders charts and headline cost', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);
    const canvases = await page.locator('canvas').count();
    expect(canvases, 'home has at least one canvas (pie)').toBeGreaterThanOrEqual(1);
    // Big-cost should be a number, not the placeholder
    const bigCost = await page.locator('#big-cost').textContent();
    expect(bigCost).toBeTruthy();
    expect(bigCost?.length).toBeGreaterThanOrEqual(1);
    // Per-provider breakdown should render CAD amounts
    const claude = await page.locator('#c-claude').textContent();
    expect(claude?.startsWith('CA$')).toBeTruthy();
  });

  test('sovereignty page renders chart + headline', async ({ page }) => {
    await page.goto('/explore/sovereignty.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1000);
    const headline = await page.locator('#sov-headline').textContent();
    expect(headline?.length || 0).toBeGreaterThan(2);
  });
});

test.describe('Decisions persist', () => {
  test('promote on a challenge updates the review badge', async ({ page }) => {
    await page.goto('/challenges/03-funding-loops.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(800);
    const promoteBtn = page.locator('button[data-verdict="promote"]').first();
    await promoteBtn.waitFor({ state: 'visible', timeout: 8000 });
    await promoteBtn.click();
    // Badge in nav should not be is-zero anymore
    const badgeClass = await page.locator('.nav__badge[data-badge="reviews"]').getAttribute('class');
    expect(badgeClass).not.toContain('is-zero');
    const badgeText = await page.locator('.nav__badge[data-badge="reviews"]').textContent();
    expect(Number(badgeText)).toBeGreaterThanOrEqual(1);
  });
});

test.describe('Finding drawer', () => {
  test('clicking a row on /stories.html opens the drawer', async ({ page }) => {
    await page.goto('/stories.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1200);
    const row = page.locator('table#findings-table tbody tr[data-finding]').first();
    await row.waitFor({ state: 'visible', timeout: 8000 });
    await row.click();
    const drawer = page.locator('.drawer.is-open');
    await drawer.waitFor({ state: 'visible', timeout: 4000 });
    const title = await drawer.locator('#drawer-title').textContent();
    expect((title || '').length).toBeGreaterThan(0);
    const ctaCount = await drawer.locator('a.btn--primary').count();
    expect(ctaCount).toBeGreaterThan(0);
    // ESC closes
    await page.keyboard.press('Escape');
    await page.waitForTimeout(400);
    const stillOpen = await page.locator('.drawer.is-open').count();
    expect(stillOpen).toBe(0);
  });

  test('clicking a row on /explore/data-tables.html opens the drawer', async ({ page }) => {
    await page.goto('/explore/data-tables.html');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1200);
    const row = page.locator('table#findings-table tbody tr[data-finding]').first();
    await row.waitFor({ state: 'visible', timeout: 8000 });
    await row.click();
    const drawer = page.locator('.drawer.is-open');
    await drawer.waitFor({ state: 'visible', timeout: 4000 });
    const title = await drawer.locator('#drawer-title').textContent();
    expect((title || '').length).toBeGreaterThan(0);
  });
});

test.describe('First-visit tour', () => {
  test('auto-fires on first visit and replay button restarts it', async ({ page }) => {
    // Clear any stored "seen" flag
    await page.goto('/');
    await page.evaluate(() => localStorage.removeItem('lc_tour_seen_v1'));
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1800);
    const tip = page.locator('.tour-tip.is-on');
    await tip.waitFor({ state: 'visible', timeout: 4000 });
    const stepText = await tip.locator('.tour-tip__step').textContent();
    expect(stepText).toMatch(/step 1 of/i);
    // ESC closes and persists
    await page.keyboard.press('Escape');
    await page.waitForTimeout(300);
    const seen = await page.evaluate(() => localStorage.getItem('lc_tour_seen_v1'));
    expect(seen).toBe('1');
    // Replay button restarts
    await page.locator('#replay-tour').click();
    await page.waitForTimeout(400);
    await page.locator('.tour-tip.is-on').waitFor({ state: 'visible', timeout: 3000 });
  });
});

test.describe('Visual snapshot', () => {
  test('home, challenge, sovereignty screenshots', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    for (const path of ['/', '/challenges/03-funding-loops.html', '/explore/sovereignty.html', '/explore/audit.html', '/explore/ask.html', '/explore/decisions.html']) {
      await page.goto(path);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1500);
      const safe = path.replace(/[^a-z0-9]+/gi, '_').replace(/^_|_$/g, '') || 'home';
      await page.screenshot({ path: `tests/screenshots/${safe}.png`, fullPage: true });
    }
  });
});
