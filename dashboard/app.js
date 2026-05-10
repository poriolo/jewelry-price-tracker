// ── Constants ────────────────────────────────────────────────────────────────

const COLORS = {
  vivara_ouro:        '#C9A84C',
  vivara_ouro_light:  'rgba(201,168,76,.15)',
  vivara_prata:       '#8A8A8A',
  vivara_prata_light: 'rgba(138,138,138,.15)',
  pandora:            '#1A1A1A',
  pandora_light:      'rgba(26,26,26,.1)',
  monte_carlo:        '#8B1A1A',
  monte_carlo_light:  'rgba(139,26,26,.12)',
};

const PANDORA_CAT_COLORS = ['#1A1A1A','#4B5563','#6B7280','#9CA3AF','#D1D5DB'];
const MC_CAT_COLORS      = ['#8B1A1A','#B91C1C','#DC2626','#EF4444'];

const PANDORA_CAT_LABELS = {
  moments: 'Moments / Berloque',
  pulseiras: 'Pulseiras',
  colares: 'Colares',
  aneis: 'Anéis',
  brincos: 'Brincos',
};
const MC_CAT_LABELS = {
  aneis: 'Anéis',
  pulseiras: 'Pulseiras',
  colares: 'Colares',
  brincos: 'Brincos',
};
const VIVARA_CAT_LABELS = {
  aneis: 'Anéis',
  pulseiras: 'Pulseiras',
  colares_pingentes: 'Colares & Pingentes',
  brincos: 'Brincos',
  relogios: 'Relógios',
};

// ── Data loading ─────────────────────────────────────────────────────────────

async function loadHistory() {
  try {
    const res = await fetch('../data/history.json');
    if (!res.ok) throw new Error(res.status);
    return await res.json();
  } catch {
    return null;
  }
}

// ── Date range filter ────────────────────────────────────────────────────────

function sliceDays(history, days) {
  if (!days || history.dates.length <= days) return history;
  const start = history.dates.length - days;
  const slicedDates = history.dates.slice(start);
  const slicedSeries = {};
  for (const [key, s] of Object.entries(history.series)) {
    slicedSeries[key] = {
      ...s,
      prices: s.prices.slice(start),
      index:  s.index.slice(start),
    };
  }
  return { ...history, dates: slicedDates, series: slicedSeries };
}

// ── Chart helpers ────────────────────────────────────────────────────────────

const chartRegistry = {};

function makeChart(id, labels, datasets, opts = {}) {
  if (chartRegistry[id]) chartRegistry[id].destroy();
  const ctx = document.getElementById(id);
  if (!ctx) return;
  chartRegistry[id] = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => {
              const val = ctx.raw;
              if (val === null || val === undefined) return null;
              if (opts.isBRL) return `${ctx.dataset.label}: R$ ${val.toFixed(2).replace('.', ',')}`;
              return `${ctx.dataset.label}: ${val.toFixed(1)}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: 'time',
          time: { unit: labels.length > 60 ? 'month' : labels.length > 14 ? 'week' : 'day',
                  tooltipFormat: 'dd/MM/yyyy' },
          ticks: { font: { size: 10 }, maxTicksLimit: 6 },
          grid: { display: false },
        },
        y: {
          ticks: {
            font: { size: 10 },
            callback: v => opts.isBRL ? `R$${(v/1000).toFixed(0)}k` : v.toFixed(0),
          },
          grid: { color: 'rgba(0,0,0,.06)' },
          ...(opts.yMin !== undefined ? { min: opts.yMin } : {}),
        },
      },
    },
  });
}

function lineDataset(label, labels, values, color, colorLight, opts = {}) {
  return {
    label,
    data: labels.map((d, i) => ({ x: d, y: values[i] })),
    borderColor: color,
    backgroundColor: colorLight || 'transparent',
    borderWidth: opts.thin ? 1.5 : 2,
    pointRadius: 0,
    tension: 0.3,
    fill: opts.fill ?? false,
  };
}

// ── % change badge ───────────────────────────────────────────────────────────

function pctChange(current, old) {
  if (!current || !old) return null;
  return ((current - old) / old) * 100;
}

function pillHtml(label, pct) {
  if (pct === null) return '';
  const sign  = pct > 0 ? '+' : '';
  const cls   = Math.abs(pct) < 0.5 ? 'pill-flat' : pct > 0 ? 'pill-up' : 'pill-down';
  return `<span class="change-pill ${cls}">${label} ${sign}${pct.toFixed(1)}%</span>`;
}

function computePills(prices, dates) {
  const last = prices.findLast(v => v !== null);
  if (!last) return '';

  function findBefore(daysAgo) {
    const target = new Date(dates.at(-1));
    target.setDate(target.getDate() - daysAgo);
    for (let i = dates.length - 1; i >= 0; i--) {
      if (new Date(dates[i]) <= target && prices[i] !== null) return prices[i];
    }
    return null;
  }

  const w1 = findBefore(7);
  const m1 = findBefore(30);
  const m3 = findBefore(90);
  return pillHtml('1S', pctChange(last, w1)) +
         pillHtml('1M', pctChange(last, m1)) +
         pillHtml('3M', pctChange(last, m3));
}

// ── Overview tab ─────────────────────────────────────────────────────────────

function renderOverview(history) {
  const s = history.series;

  // Summary index lines: one per brand (pick the most representative series)
  const overviewKeys = [
    { key: 'vivara_aneis_ouro',  label: 'Vivara Ouro',     color: COLORS.vivara_ouro,    light: COLORS.vivara_ouro_light },
    { key: 'vivara_aneis_prata', label: 'Vivara Prata',    color: COLORS.vivara_prata,   light: COLORS.vivara_prata_light },
    { key: 'pandora_moments',    label: 'Pandora Moments', color: COLORS.pandora,         light: COLORS.pandora_light },
    { key: 'monte_carlo_aneis',  label: 'Monte Carlo',     color: COLORS.monte_carlo,     light: COLORS.monte_carlo_light },
  ];

  const datasets = overviewKeys
    .filter(({ key }) => s[key])
    .map(({ key, label, color, light }) =>
      lineDataset(label, history.dates, s[key].index, color, light)
    );

  makeChart('chart-index', history.dates, datasets, { yMin: 85 });

  // Brand summary badges
  const badgeContainer = document.getElementById('brand-badges');
  badgeContainer.innerHTML = '';

  const brandGroups = [
    {
      brand: 'Vivara', color: COLORS.vivara_ouro,
      rows: [
        { label: 'Anéis Ouro',    key: 'vivara_aneis_ouro' },
        { label: 'Anéis Prata',   key: 'vivara_aneis_prata' },
        { label: 'Pulseiras Ouro',key: 'vivara_pulseiras_ouro' },
        { label: 'Pulseiras Prata',key:'vivara_pulseiras_prata' },
        { label: 'Colares Ouro',  key: 'vivara_colares_ouro' },
        { label: 'Colares Prata', key: 'vivara_colares_prata' },
        { label: 'Brincos Ouro',  key: 'vivara_brincos_ouro' },
        { label: 'Brincos Prata', key: 'vivara_brincos_prata' },
      ],
    },
    {
      brand: 'Pandora', color: COLORS.pandora,
      rows: Object.entries(PANDORA_CAT_LABELS).map(([k, l]) => ({ label: l, key: `pandora_${k}` })),
    },
    {
      brand: 'Monte Carlo', color: COLORS.monte_carlo,
      rows: Object.entries(MC_CAT_LABELS).map(([k, l]) => ({ label: l, key: `monte_carlo_${k}` })),
    },
  ];

  for (const group of brandGroups) {
    const el = document.createElement('div');
    el.className = 'brand-badge';
    const lastDate = history.dates.at(-1);
    let rowsHtml = '';
    for (const { label, key } of group.rows) {
      if (!s[key]) continue;
      const prices  = s[key].prices;
      const last    = prices.findLast(v => v !== null);
      if (!last) continue;
      const pills   = computePills(prices, history.dates);
      rowsHtml += `
        <div class="flex items-center justify-between py-1 border-b border-gray-50 last:border-0">
          <span class="text-xs text-gray-600 font-medium">${label}</span>
          <div class="flex items-center gap-2">
            <span class="text-xs font-semibold">R$&nbsp;${last.toLocaleString('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:0})}</span>
            <div class="badge-row">${pills}</div>
          </div>
        </div>`;
    }
    el.innerHTML = `
      <p class="brand-badge-name" style="color:${group.color}">${group.brand}</p>
      ${rowsHtml || '<p class="text-xs text-gray-400">Sem dados ainda</p>'}`;
    badgeContainer.appendChild(el);
  }
}

// ── Vivara tab ───────────────────────────────────────────────────────────────

function renderVivara(history) {
  const s = history.series;

  // Ouro vs Prata aggregate (average all categories)
  function aggPrices(keys) {
    return history.dates.map((_, i) => {
      const vals = keys.map(k => s[k]?.prices[i]).filter(v => v !== null && v !== undefined);
      return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    });
  }

  const ouroKeys  = ['vivara_aneis_ouro','vivara_pulseiras_ouro','vivara_colares_ouro','vivara_brincos_ouro'];
  const prataKeys = ['vivara_aneis_prata','vivara_pulseiras_prata','vivara_colares_prata','vivara_brincos_prata'];

  makeChart('chart-vivara-material', history.dates, [
    lineDataset('Ouro (média)',  history.dates, aggPrices(ouroKeys),  COLORS.vivara_ouro,  COLORS.vivara_ouro_light,  { fill: true }),
    lineDataset('Prata (média)', history.dates, aggPrices(prataKeys), COLORS.vivara_prata, COLORS.vivara_prata_light, { fill: true }),
  ], { isBRL: true });

  // Subcategory mini-charts
  const container = document.getElementById('vivara-subcats');
  container.innerHTML = '';

  const subcats = [
    { label: 'Anéis',              ouro: 'vivara_aneis_ouro',      prata: 'vivara_aneis_prata' },
    { label: 'Pulseiras',          ouro: 'vivara_pulseiras_ouro',  prata: 'vivara_pulseiras_prata' },
    { label: 'Colares & Pingentes',ouro: 'vivara_colares_ouro',    prata: 'vivara_colares_prata' },
    { label: 'Brincos',            ouro: 'vivara_brincos_ouro',    prata: 'vivara_brincos_prata' },
    { label: 'Relógios',           ouro: 'vivara_relogios',        prata: null },
  ];

  for (const sub of subcats) {
    const card = document.createElement('div');
    card.className = 'mini-card';
    const canvasId = `mini-${sub.label.replace(/\W+/g, '-')}`;
    card.innerHTML = `<h3>${sub.label}</h3><div class="mini-chart-wrap"><canvas id="${canvasId}"></canvas></div>`;
    container.appendChild(card);

    const datasets = [];
    if (sub.ouro && s[sub.ouro]) {
      datasets.push(lineDataset('Ouro', history.dates, s[sub.ouro].prices, COLORS.vivara_ouro, null, { thin: true }));
    }
    if (sub.prata && s[sub.prata]) {
      datasets.push(lineDataset('Prata', history.dates, s[sub.prata].prices, COLORS.vivara_prata, null, { thin: true }));
    }
    if (datasets.length) {
      makeChart(canvasId, history.dates, datasets, { isBRL: true });
    }
  }
}

// ── Pandora tab ──────────────────────────────────────────────────────────────

function renderPandora(history) {
  const s = history.series;
  const cats = Object.keys(PANDORA_CAT_LABELS);
  const datasets = cats
    .filter(cat => s[`pandora_${cat}`])
    .map((cat, i) =>
      lineDataset(PANDORA_CAT_LABELS[cat], history.dates, s[`pandora_${cat}`].prices,
                  PANDORA_CAT_COLORS[i], null, { thin: true })
    );

  makeChart('chart-pandora', history.dates, datasets, { isBRL: true });

  const container = document.getElementById('pandora-badges');
  container.innerHTML = '';
  for (const [cat, label] of Object.entries(PANDORA_CAT_LABELS)) {
    const key = `pandora_${cat}`;
    if (!s[key]) continue;
    const last = s[key].prices.findLast(v => v !== null);
    if (!last) continue;
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = `
      <p class="text-xs font-semibold text-gray-700 mb-1">${label}</p>
      <p class="text-lg font-bold">R$&nbsp;${last.toLocaleString('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:0})}</p>
      <div class="badge-row mt-1">${computePills(s[key].prices, history.dates)}</div>`;
    container.appendChild(el);
  }
}

// ── Monte Carlo tab ──────────────────────────────────────────────────────────

function renderMonteCarlo(history) {
  const s = history.series;
  const cats = Object.keys(MC_CAT_LABELS);
  const datasets = cats
    .filter(cat => s[`monte_carlo_${cat}`])
    .map((cat, i) =>
      lineDataset(MC_CAT_LABELS[cat], history.dates, s[`monte_carlo_${cat}`].prices,
                  MC_CAT_COLORS[i], null, { thin: true })
    );

  makeChart('chart-monte-carlo', history.dates, datasets, { isBRL: true });

  const container = document.getElementById('monte-carlo-badges');
  container.innerHTML = '';
  for (const [cat, label] of Object.entries(MC_CAT_LABELS)) {
    const key = `monte_carlo_${cat}`;
    if (!s[key]) continue;
    const last = s[key].prices.findLast(v => v !== null);
    if (!last) continue;
    const el = document.createElement('div');
    el.className = 'card';
    el.innerHTML = `
      <p class="text-xs font-semibold text-gray-700 mb-1">${label}</p>
      <p class="text-lg font-bold">R$&nbsp;${last.toLocaleString('pt-BR',{minimumFractionDigits:0,maximumFractionDigits:0})}</p>
      <div class="badge-row mt-1">${computePills(s[key].prices, history.dates)}</div>`;
    container.appendChild(el);
  }
}

// ── Tab routing ──────────────────────────────────────────────────────────────

let currentHistory = null;
let currentDays    = 30;

function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.add('hidden'));
  document.getElementById(`tab-${tabId}`)?.classList.remove('hidden');
  if (currentHistory) renderTab(tabId, sliceDays(currentHistory, currentDays));
}

function renderTab(tabId, history) {
  if (tabId === 'overview')     renderOverview(history);
  if (tabId === 'vivara')       renderVivara(history);
  if (tabId === 'pandora')      renderPandora(history);
  if (tabId === 'monte-carlo')  renderMonteCarlo(history);
}

function activeTab() {
  return document.querySelector('.tab-btn.active')?.dataset.tab || 'overview';
}

// ── Range selector ───────────────────────────────────────────────────────────

document.querySelectorAll('.range-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentDays = parseInt(btn.dataset.days, 10);
    if (currentHistory) renderTab(activeTab(), sliceDays(currentHistory, currentDays));
  });
});

// ── Tab click listeners ──────────────────────────────────────────────────────

document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

// ── Init ─────────────────────────────────────────────────────────────────────

(async () => {
  const history = await loadHistory();

  if (!history || !history.dates?.length) {
    document.getElementById('error-overlay').classList.remove('hidden');
    return;
  }

  currentHistory = history;
  document.getElementById('status-dot').className = 'w-2 h-2 rounded-full bg-green-400';

  const lastDate = new Date(history.dates.at(-1)).toLocaleDateString('pt-BR');
  document.getElementById('last-updated').textContent = `Última atualização: ${lastDate}`;

  renderTab('overview', sliceDays(history, currentDays));
})();
