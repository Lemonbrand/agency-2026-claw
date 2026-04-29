// @ts-check
import { test, expect } from '@playwright/test';

const ROUTES = [
  { path: '/',                                       title: /Agency 2026/, marker: 'h1, .pill-money' },
  { path: '/index.html',                             title: /Agency 2026/, marker: 'h1, .pill-money' },
  { path: '/stories.html',                           title: /Findings/i,   marker: 'h1, .hero-h1' },
  { path: '/trust.html',                             title: /Evidence|Trust/i, marker: 'h1, .h1' },
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
    // Per-provider breakdown should render dollar amounts
    const claude = await page.locator('#c-claude').textContent();
    expect(claude?.startsWith('$')).toBeTruthy();
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
