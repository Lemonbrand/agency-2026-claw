/**
 * Chart.js wrappers reading the backend-curated charts/*.json bundles.
 * No raw findings parsed in browser. Each chart has a single intended message.
 */

import { Chart, registerables } from 'chart.js';
import { SankeyController, Flow } from 'chartjs-chart-sankey';
import 'chartjs-adapter-date-fns';
import { loadChartData } from './manifest.js';

Chart.register(...registerables, SankeyController, Flow);

const FONT = '"DM Sans", system-ui, sans-serif';
const MONO = '"JetBrains Mono", ui-monospace, monospace';

const PALETTE = {
  green:  'hsl(145, 63%, 42%)',
  amber:  'hsl(38, 90%, 52%)',
  red:    'hsl(0, 62%, 48%)',
  navy:   'hsl(207, 30%, 24%)',
  orange: 'hsl(28, 79%, 52%)',
  ink2:   'hsl(199, 6%, 42%)',
  ink3:   'hsl(200, 8%, 62%)',
  border: 'hsl(200, 12%, 85%)',
};

Chart.defaults.font.family = FONT;
Chart.defaults.font.size = 12;
Chart.defaults.color = PALETTE.ink2;
Chart.defaults.borderColor = PALETTE.border;

function colorByThreshold(value, thresholds) {
  if (value > (thresholds?.concentrated ?? 2500)) return PALETTE.red;
  if (value > (thresholds?.competitive ?? 1500)) return PALETTE.amber;
  return PALETTE.green;
}

export async function renderHHI(canvasEl, captionEl) {
  const data = await loadChartData('hhi-by-department');
  if (data._missing || !Array.isArray(data.data) || data.data.length === 0) {
    canvasEl.replaceWith(emptyState('HHI distribution will appear once the backend probe completes.'));
    return;
  }
  const labels = data.data.map(d => d.department);
  const values = data.data.map(d => d.hhi);
  const colors = values.map(v => colorByThreshold(v, data.thresholds));

  new Chart(canvasEl, {
    type: 'bar',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderRadius: 4 }] },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const row = data.data[ctx.dataIndex];
              return [
                `HHI ${row.hhi.toLocaleString()}`,
                `Top vendor: ${row.top_vendor} (${(row.top_share * 100).toFixed(1)}%)`,
                `Programs: ${row.program_count}`,
              ];
            },
          },
        },
        annotation: undefined,
      },
      scales: {
        x: { beginAtZero: true, grid: { color: PALETTE.border } },
        y: { ticks: { font: { size: 11 } } },
      },
    },
  });

  if (captionEl && data.caption) captionEl.textContent = data.caption;
}

export async function renderSankey(canvasEl, captionEl) {
  const data = await loadChartData('tri-jurisdictional-sankey');
  if (data._missing || !Array.isArray(data.links) || data.links.length === 0) {
    canvasEl.replaceWith(emptyState('Sankey will appear once the backend produces the cross-jurisdictional roll-up.'));
    return;
  }

  new Chart(canvasEl, {
    type: 'sankey',
    data: {
      datasets: [{
        data: data.links.map(l => ({ from: l.source, to: l.target, flow: l.value })),
        colorFrom: () => PALETTE.navy,
        colorTo: () => PALETTE.orange,
        colorMode: 'gradient',
        labels: Object.fromEntries((data.nodes || []).map(n => [n.id, n.label])),
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
    },
  });

  if (captionEl && data.caption) captionEl.textContent = data.caption;
}

export async function renderCostOverTime(canvasEl, captionEl) {
  const data = await loadChartData('cost-over-time');
  if (data._missing || !Array.isArray(data.series) || data.series.length === 0) {
    canvasEl.replaceWith(emptyState('Cost timeline will appear once the sovereignty tracker has at least one full hour of data.'));
    return;
  }

  const datasets = data.series.map((s, i) => {
    const colorMap = {
      anthropic: PALETTE.navy,
      openai:    PALETTE.orange,
      openrouter: PALETTE.amber,
      cohere:    PALETTE.green,
    };
    const color = colorMap[s.provider] || ['#666', PALETTE.navy, PALETTE.orange][i % 3];
    return {
      label: s.label || s.provider,
      data: s.points.map(p => ({ x: p.ts, y: p.cost_usd })),
      borderColor: color,
      backgroundColor: color + '33',
      fill: true,
      tension: 0.18,
      pointRadius: 0,
      pointHoverRadius: 4,
    };
  });

  new Chart(canvasEl, {
    type: 'line',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 14, font: { size: 11 } } },
      },
      scales: {
        x: { type: 'time', time: { unit: 'hour' }, grid: { color: PALETTE.border } },
        y: { stacked: true, beginAtZero: true, grid: { color: PALETTE.border }, ticks: { callback: v => '$' + Number(v).toFixed(2) } },
      },
    },
  });

  if (captionEl && data.caption) captionEl.textContent = data.caption;
}

function emptyState(message) {
  const div = document.createElement('div');
  div.className = 'empty';
  div.textContent = message;
  return div;
}
