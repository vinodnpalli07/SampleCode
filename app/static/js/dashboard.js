const summaryEndpoint = '/api/dashboard/summary';
const runsEndpoint = '/api/dashboard/recent-runs';
const errorsEndpoint = '/api/dashboard/common-errors';

let passRateChart;
let errorBreakdownChart;

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('apply-filters').addEventListener('click', () => refreshDashboard());
  refreshDashboard();
});

async function refreshDashboard() {
  const filters = collectFilters();
  await Promise.all([
    renderSummary(filters),
    renderRuns(filters),
    renderCommonErrors(filters),
  ]);
}

function collectFilters() {
  const plan = document.getElementById('filter-plan').value.trim();
  const environment = document.getElementById('filter-environment').value.trim();
  const status = document.getElementById('filter-status').value.trim();
  const filters = {};
  if (plan) filters.plan = plan;
  if (environment) filters.environment = environment;
  if (status) filters.status = status;
  return filters;
}

async function renderSummary(filters) {
  const params = new URLSearchParams(filters).toString();
  const response = await fetch(`${summaryEndpoint}?${params}`);
  const data = await response.json();

  const kpiContainer = document.getElementById('kpi-cards');
  kpiContainer.innerHTML = '';

  const kpis = [
    { label: 'Total Runs', value: data.runs },
    { label: 'Total Tests', value: data.total_tests },
    { label: 'Pass Rate', value: toPercent(data.pass_rate) },
    { label: 'Fail Rate', value: toPercent(data.fail_rate) },
    { label: 'Blocked Rate', value: toPercent(data.blocked_rate) },
    { label: 'Avg Duration', value: formatDuration(data.avg_duration_seconds) },
  ];

  kpis.forEach((kpi) => {
    const card = document.createElement('div');
    card.className = 'kpi-card';
    card.innerHTML = `<h3>${kpi.label}</h3><span>${kpi.value}</span>`;
    kpiContainer.appendChild(card);
  });
}

async function renderRuns(filters) {
  const params = new URLSearchParams({ ...filters, limit: 30 }).toString();
  const response = await fetch(`${runsEndpoint}?${params}`);
  const runs = await response.json();

  const tbody = document.querySelector('#runs-table tbody');
  tbody.innerHTML = '';

  const passRates = [];
  const runLabels = [];

  runs.forEach((run) => {
    const passRate = run.aggregated_metrics?.pass_rate ?? (run.passed_tests / (run.total_tests || 1));
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${run.run_id}</td>
      <td>${run.plan}${run.suite ? ' / ' + run.suite : ''}</td>
      <td>${run.status}</td>
      <td>${toPercent(passRate)}</td>
      <td>${run.failed_tests}</td>
      <td>${formatDuration(run.duration_seconds)}</td>
      <td>${formatDate(run.start_time)}</td>
    `;
    tbody.appendChild(row);

    passRates.push(Math.round((passRate || 0) * 100));
    runLabels.push(run.run_id);
  });

  passRates.reverse();
  runLabels.reverse();

  const ctx = document.getElementById('passRateChart');
  if (passRateChart) {
    passRateChart.destroy();
  }
  passRateChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: runLabels,
      datasets: [
        {
          label: 'Pass %',
          data: passRates,
          borderColor: '#1f6feb',
          backgroundColor: 'rgba(31, 111, 235, 0.2)',
          tension: 0.3,
          fill: true,
        },
      ],
    },
    options: {
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          ticks: { callback: (value) => `${value}%` },
        },
      },
    },
  });
}

async function renderCommonErrors(filters) {
  const params = new URLSearchParams({ limit: 12, ...filters }).toString();
  const response = await fetch(`${errorsEndpoint}?${params}`);
  const errors = await response.json();

  const list = document.getElementById('common-errors');
  list.innerHTML = '';

  const labels = [];
  const counts = [];

  errors.forEach((error) => {
    const item = document.createElement('li');
    item.innerHTML = `
      <span>
        <strong>${error.summary}</strong><br/>
        <small>${error.category || 'Uncategorized'}</small>
      </span>
      <span class="badge">${error.occurrences || 0}</span>
    `;
    list.appendChild(item);

    labels.push(error.summary);
    counts.push(error.occurrences || 0);
  });

  const ctx = document.getElementById('errorBreakdownChart');
  if (errorBreakdownChart) {
    errorBreakdownChart.destroy();
  }
  errorBreakdownChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Occurrences',
          data: counts,
          backgroundColor: '#f85149',
        },
      ],
    },
    options: {
      indexAxis: 'y',
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: { beginAtZero: true },
      },
    },
  });
}

function toPercent(value) {
  if (value === null || value === undefined) return '0%';
  return `${Math.round(value * 100)}%`;
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '—';
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins === 0) return `${secs}s`;
  return `${mins}m ${secs}s`;
}

function formatDate(isoString) {
  if (!isoString) return '—';
  const date = new Date(isoString);
  return date.toLocaleString();
}
