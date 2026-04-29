// @ts-check
import { test } from '@playwright/test';

test('extract data center coordinates from the SVG', async ({ page }) => {
  await page.goto('/tests/_calibrate-map.html');
  await page.waitForFunction(() => document.body.dataset.ready === 'yes', { timeout: 10000 });
  const calib = await page.evaluate(() => window._calibration);
  console.log('CALIBRATION', JSON.stringify(calib, null, 2));

  // Approximate lat/lng for our points of interest. We pick an intra-state
  // anchor (e.g. SF Bay area within CA), so we use a bbox-fraction within each
  // state to land closer to the actual datacenter city.
  const anchors = [
    { city: 'San Francisco', state: 'US-CA', country: 'US', fx: 0.10, fy: 0.30 },  // northwest CA
    { city: 'Oregon (US-West-2)', state: 'US-OR', country: 'US', fx: 0.30, fy: 0.55 },
    { city: 'Northern Virginia (US-East-1)', state: 'US-VA', country: 'US', fx: 0.20, fy: 0.30 },
    { city: 'Texas (Dallas)', state: 'US-TX', country: 'US', fx: 0.55, fy: 0.40 },
    { city: 'New York / NJ', state: 'US-NY', country: 'US', fx: 0.55, fy: 0.55 },
    { city: 'Toronto', state: 'CA-ON', country: 'CA', fx: 0.62, fy: 0.86 },
  ];

  const out = [];
  for (const a of anchors) {
    const r = calib.results[a.state];
    if (!r) { out.push({ ...a, error: 'state not found' }); continue; }
    out.push({ ...a, x: Math.round(r.x + r.w * a.fx), y: Math.round(r.y + r.h * a.fy) });
  }
  console.log('MARKERS', JSON.stringify(out, null, 2));

  await page.evaluate((markers) => {
    const svg = document.querySelector('#root svg');
    const ns = 'http://www.w3.org/2000/svg';
    for (const m of markers) {
      if (m.error) continue;
      const c = document.createElementNS(ns, 'circle');
      c.setAttribute('cx', m.x); c.setAttribute('cy', m.y);
      c.setAttribute('r', 14);
      c.setAttribute('fill', m.country === 'CA' ? 'red' : 'blue');
      c.setAttribute('opacity', '0.85');
      svg.appendChild(c);
    }
  }, out);

  await page.screenshot({ path: 'tests/screenshots/map-calibration.png', fullPage: true });
});
