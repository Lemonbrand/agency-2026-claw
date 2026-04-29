/**
 * North America datacenter map.
 *
 * Uses d3-geo + topojson-client. Real projection math, real GPS coords,
 * real city placement. No calibration.
 *
 *   buildMap(containerEl, { width, height, cities, focus });
 *
 * Cities are placed via projection([lng, lat]). The map auto-fits the
 * container, so markers and country outlines are guaranteed to align.
 */

import { geoMercator, geoPath } from 'd3-geo';
import { feature, mesh } from 'topojson-client';
import countriesTopo from 'world-atlas/countries-110m.json';
import statesTopo from 'us-atlas/states-10m.json';

const DEFAULT_CITIES = [
  { lng: -122.42, lat: 37.77, label: 'San Francisco', color: 'us', size: 'lg', labelOffset: -34 },
  { lng: -119.70, lat: 45.66, label: 'Oregon',        color: 'us', size: 'md', labelOffset: -22 },
  { lng:  -77.49, lat: 39.02, label: 'N. Virginia',   color: 'us', size: 'lg', labelOffset: 32 },
  { lng:  -96.80, lat: 32.78, label: 'Texas',         color: 'us', size: 'md', labelOffset: 32 },
  { lng:  -74.00, lat: 40.71, label: 'New York',      color: 'us', size: 'md', labelOffset: -22 },
  { lng:  -79.38, lat: 43.65, label: 'Toronto · Cohere', color: 'ca', size: 'lg', labelOffset: -34 },
];

const COLOR = {
  us: { fill: 'hsl(216, 90%, 48%)', text: 'hsl(216, 90%, 25%)' },
  ca: { fill: 'hsl(0, 80%, 48%)',   text: 'hsl(0, 70%, 32%)' },
};
const SIZE = { md: { r: 4, halo: 9, font: 10 }, lg: { r: 6, halo: 14, font: 11 } };
const NS = 'http://www.w3.org/2000/svg';

/**
 * Render the North America map into containerEl. The element should be a
 * positioned container (relative). The SVG fills its width and a derived
 * height. Pass cities=[] to suppress markers; pass nothing for our defaults.
 */
export async function buildMap(containerEl, opts = {}) {
  const cities = opts.cities ?? DEFAULT_CITIES;
  const naBounds = opts.bounds ?? [[-170, 14], [-50, 72]];  // [west, south] [east, north]

  // Container size
  const rect = containerEl.getBoundingClientRect();
  const width = Math.max(420, Math.floor(rect.width || 800));
  const height = opts.height ?? Math.min(420, Math.round(width * 0.62));

  // Pull country + state geometries
  const countries = feature(countriesTopo, countriesTopo.objects.countries).features;
  const us = countries.find(c => c.id === '840' || c.properties.name === 'United States of America' || c.properties.name === 'United States');
  const ca = countries.find(c => c.id === '124' || c.properties.name === 'Canada');
  const mx = countries.find(c => c.id === '484' || c.properties.name === 'Mexico');

  // Mercator clipped to the North America window. Mercator is fine for a
  // continent-scale view and keeps city dots visually grounded.
  const focusFeature = { type: 'FeatureCollection', features: [us, ca, mx].filter(Boolean) };
  const projection = geoMercator().fitSize([width, height], focusFeature);
  const path = geoPath(projection);

  // Build the SVG
  const svg = document.createElementNS(NS, 'svg');
  svg.setAttribute('width', width);
  svg.setAttribute('height', height);
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.style.maxWidth = '100%';

  const land = document.createElementNS(NS, 'g');
  land.setAttribute('id', 'land');

  // Mexico (de-emphasized context)
  if (mx) {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', path(mx));
    p.setAttribute('fill', 'hsl(200, 12%, 88%)');
    p.setAttribute('stroke', 'hsl(0, 0%, 100%)');
    p.setAttribute('stroke-width', '1');
    land.appendChild(p);
  }
  // US
  if (us) {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', path(us));
    p.setAttribute('fill', 'hsl(200, 12%, 80%)');
    p.setAttribute('stroke', 'hsl(0, 0%, 100%)');
    p.setAttribute('stroke-width', '1');
    land.appendChild(p);
  }
  // Canada (slightly different shade)
  if (ca) {
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', path(ca));
    p.setAttribute('fill', 'hsl(200, 12%, 76%)');
    p.setAttribute('stroke', 'hsl(0, 0%, 100%)');
    p.setAttribute('stroke-width', '1');
    land.appendChild(p);
  }

  // US state borders as a single mesh
  try {
    const stateMesh = mesh(statesTopo, statesTopo.objects.states, (a, b) => a !== b);
    const p = document.createElementNS(NS, 'path');
    p.setAttribute('d', path(stateMesh));
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke', 'hsl(0, 0%, 100%)');
    p.setAttribute('stroke-width', '0.7');
    p.setAttribute('opacity', '0.85');
    land.appendChild(p);
  } catch { /* state mesh is decoration; skip silently if it fails */ }

  svg.appendChild(land);

  // City markers
  const markers = document.createElementNS(NS, 'g');
  markers.setAttribute('id', 'markers');

  for (const city of cities) {
    const xy = projection([city.lng, city.lat]);
    if (!xy) continue;
    const [cx, cy] = xy;
    const sz = SIZE[city.size] || SIZE.md;
    const col = COLOR[city.color] || COLOR.us;

    const g = document.createElementNS(NS, 'g');

    const halo = document.createElementNS(NS, 'circle');
    halo.setAttribute('cx', cx);
    halo.setAttribute('cy', cy);
    halo.setAttribute('r', sz.halo);
    halo.setAttribute('fill', col.fill);
    halo.setAttribute('opacity', city.color === 'ca' ? '0.32' : '0.22');
    if (city.color === 'ca') {
      const an1 = document.createElementNS(NS, 'animate');
      an1.setAttribute('attributeName', 'r');
      an1.setAttribute('values', `${sz.halo};${sz.halo + 8};${sz.halo}`);
      an1.setAttribute('dur', '2.5s');
      an1.setAttribute('repeatCount', 'indefinite');
      halo.appendChild(an1);
      const an2 = document.createElementNS(NS, 'animate');
      an2.setAttribute('attributeName', 'opacity');
      an2.setAttribute('values', '0.32;0.12;0.32');
      an2.setAttribute('dur', '2.5s');
      an2.setAttribute('repeatCount', 'indefinite');
      halo.appendChild(an2);
    }
    g.appendChild(halo);

    const dot = document.createElementNS(NS, 'circle');
    dot.setAttribute('cx', cx);
    dot.setAttribute('cy', cy);
    dot.setAttribute('r', sz.r);
    dot.setAttribute('fill', col.fill);
    dot.setAttribute('opacity', '0.97');
    g.appendChild(dot);

    const text = document.createElementNS(NS, 'text');
    text.setAttribute('x', cx);
    text.setAttribute('y', cy + (city.labelOffset ?? -sz.halo - 4));
    text.setAttribute('font-family', 'JetBrains Mono, ui-monospace, monospace');
    text.setAttribute('font-size', sz.font);
    text.setAttribute('fill', col.text);
    text.setAttribute('text-anchor', 'middle');
    if (city.size === 'lg') text.setAttribute('font-weight', '700');
    text.textContent = city.label;
    g.appendChild(text);

    markers.appendChild(g);
  }

  svg.appendChild(markers);

  // Mount
  containerEl.replaceChildren(svg);
  return { svg, projection };
}
