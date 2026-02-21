/**
 * Jackdaw Sentry Dashboard JavaScript
 * All stat cards and charts are wired to live API data.
 */

var volumeChart = null;
var riskChart = null;
var alertsData = [];
var wsConnection = null;

document.addEventListener('DOMContentLoaded', function () {
    if (typeof lucide !== 'undefined') lucide.createIcons();
    var yearEl = document.getElementById('jds-year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();
    initializeCharts();
    loadInitialData();
    startWebSocketConnection();
    startPeriodicUpdates();
});


function initializeCharts() {
    var c = JDS.chartColors();
    var days = JDS.lastNDaysShort(7);

    // Volume chart — placeholder zeros; updated by loadDashboardStats()
    var volumeCtx = document.getElementById('volume-chart');
    if (volumeCtx) {
        volumeChart = new Chart(volumeCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: days,
                datasets: [{
                    label: 'Transactions',
                    data: [0, 0, 0, 0, 0, 0, 0],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59,130,246,0.1)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { color: c.text, callback: function (v) { return v.toLocaleString(); } }, grid: { color: c.grid } },
                    x: { ticks: { color: c.text }, grid: { display: false } }
                }
            }
        });
    }

    // Priority chart — placeholder zeros; updated by loadInvestigationStats()
    var riskCtx = document.getElementById('risk-chart');
    if (riskCtx) {
        riskChart = new Chart(riskCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Critical', 'High', 'Medium', 'Low'],
                datasets: [{
                    data: [0, 0, 0, 0],
                    backgroundColor: ['#ef4444', '#f59e0b', '#3b82f6', '#94a3b8'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right', labels: { color: c.text, padding: 16 } } }
            }
        });
    }
}

async function loadInitialData() {
    await Promise.all([
        loadSanctionsStats(),
        loadBlockchainStats(),
        loadInvestigationStats(),
        loadRecentAlerts()
    ]);
}

// Stat 1: sanctioned addresses from sanctions API
async function loadSanctionsStats() {
    try {
        var data = await Auth.fetchJSON('/api/v1/sanctions/statistics');
        var total = data && data.statistics ? data.statistics.total_sanctioned : 0;
        JDS.updateStatCard('total-transactions', total.toLocaleString(), true);
        var sub = document.getElementById('stat-sanctions-sub');
        if (sub) {
            var src = data && data.statistics && data.statistics.by_source ? data.statistics.by_source : {};
            var parts = Object.entries(src).map(function (kv) { return kv[0].replace('_', ' ') + ': ' + kv[1]; });
            sub.textContent = parts.length ? parts.join(' · ') : 'OFAC & EU lists';
        }
    } catch (_) {
        JDS.updateStatCard('total-transactions', '—', false);
    }
}

// Stat 4 + volume chart: blockchain statistics
async function loadBlockchainStats() {
    try {
        var stats = await Auth.fetchJSON('/api/v1/blockchain/statistics');
        var s = stats && stats.statistics ? stats.statistics : stats || {};
        JDS.updateStatCard('blockchains', (s.supported_blockchains || 0), true);
        if (volumeChart) {
            var vol = Array.isArray(s.volume_data) && s.volume_data.length === 7 ? s.volume_data : [0,0,0,0,0,0,0];
            volumeChart.data.datasets[0].data = vol;
            volumeChart.update();
        }
    } catch (_) {
        // query blockchain/supported to at least count chains
        try {
            var sup = await Auth.fetchJSON('/api/v1/blockchain/supported');
            var chains = sup && sup.blockchains ? Object.keys(sup.blockchains).length : 0;
            JDS.updateStatCard('blockchains', chains, true);
        } catch (_2) {
            JDS.updateStatCard('blockchains', '—', false);
        }
    }
}

// Stats 2 (alerts) + 3 (investigations) + priority chart
async function loadInvestigationStats() {
    try {
        var data = await Auth.fetchJSON('/api/v1/investigations/list?limit=200');
        var items = Array.isArray(data) ? data : (data && data.investigations ? data.investigations : []);
        var open = items.filter(function (i) { return i.status === 'open' || i.status === 'in_progress'; }).length;
        JDS.updateStatCard('avg-risk-score', open, true);
        var sub = document.getElementById('stat-inv-sub');
        if (sub) sub.textContent = 'of ' + items.length + ' total cases';

        // Update priority chart with real counts
        if (riskChart) {
            var counts = { critical: 0, high: 0, medium: 0, low: 0 };
            items.forEach(function (i) { var p = i.priority || 'medium'; if (counts[p] !== undefined) counts[p]++; });
            riskChart.data.datasets[0].data = [counts.critical, counts.high, counts.medium, counts.low];
            riskChart.update();
        }
    } catch (_) {
        JDS.updateStatCard('avg-risk-score', '—', false);
    }
}

async function loadRecentAlerts() {
    try {
        var data = await Auth.fetchJSON('/api/v1/alerts/recent?limit=10');
        var alerts = Array.isArray(data) ? data : (data && data.alerts ? data.alerts : []);
        var total = (data && data.pagination && data.pagination.total_count != null) ? data.pagination.total_count : alerts.length;
        JDS.updateStatCard('active-alerts', total, true);
        var sub = document.getElementById('stat-alerts-sub');
        if (sub) sub.textContent = 'last 24 h';
        alertsData = alerts.slice(0, 10);
        updateAlertsTable(alertsData);
    } catch (_) {
        // fallback: try intelligence alerts
        try {
            var data2 = await Auth.fetchJSON('/api/v1/intelligence/alerts?limit=10');
            var alerts2 = Array.isArray(data2) ? data2 : (data2 && data2.alerts ? data2.alerts : []);
            JDS.updateStatCard('active-alerts', alerts2.length, true);
            alertsData = alerts2;
            updateAlertsTable(alerts2.length ? alerts2 : []);
        } catch (_2) {
            JDS.updateStatCard('active-alerts', 0, true);
            updateAlertsTable([]);
        }
    }
}

function updateAlertsTable(alerts) {
    var tableBody = document.getElementById('alerts-table');
    if (!tableBody) return;

    var loadingRow = tableBody.querySelector('.alerts-loading');
    if (loadingRow) loadingRow.remove();

    var emptyRow = tableBody.querySelector('.alerts-empty');
    if (!emptyRow) {
        emptyRow = document.createElement('tr');
        emptyRow.className = 'alerts-empty hidden';
        emptyRow.innerHTML = '<td colspan="6" class="py-8 text-center text-slate-400">No alerts found</td>';
        tableBody.appendChild(emptyRow);
    }

    Array.from(tableBody.querySelectorAll('tr:not(.alerts-empty)')).forEach(function (r) { r.remove(); });

    if (!alerts.length) {
        emptyRow.classList.remove('hidden');
    } else {
        emptyRow.classList.add('hidden');
        alerts.forEach(function (alert) {
            var row = createAlertRow(alert);
            tableBody.insertBefore(row, emptyRow);
        });
    }
}

function createAlertRow(alert) {
    var row = document.createElement('tr');
    row.className = 'border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50 fade-in';
    var risk = alert.risk || alert.risk_score || 0;
    var riskCls = risk >= 0.8 ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300' : risk >= 0.6 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' : risk >= 0.4 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300';
    var statusColors = { active: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300', investigating: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300', resolved: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400', pending: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' };
    var st = alert.status || 'active';
    var stCls = statusColors[st] || statusColors.active;
    var addr = alert.address || '—';
    var shortAddr = addr.length > 16 ? addr.substring(0, 10) + '...' + addr.substring(addr.length - 6) : addr;

    var esc = JDS.escapeHTML;
    row.innerHTML = '<td class="py-3 px-4 font-medium">' + esc(alert.type || alert.alert_type || alert.title || '—') + '</td>'
        + '<td class="py-3 px-4 text-slate-500 dark:text-slate-400 font-mono text-xs">' + esc(shortAddr) + '</td>'
        + '<td class="py-3 px-4 text-slate-500 dark:text-slate-400">' + esc(alert.blockchain || '—') + '</td>'
        + '<td class="py-3 px-4"><span class="px-2 py-1 rounded-full text-xs font-semibold ' + riskCls + '">' + (risk * 100).toFixed(0) + '%</span></td>'
        + '<td class="py-3 px-4 text-slate-500 dark:text-slate-400">' + esc(JDS.formatTime(alert.time || alert.created_at)) + '</td>'
        + '<td class="py-3 px-4"><span class="px-2 py-1 rounded-full text-xs font-semibold ' + stCls + '">' + esc(st) + '</span></td>';
    return row;
}


function startWebSocketConnection() {
    try {
        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        var wsUrl = protocol + '//' + window.location.host + '/ws/dashboard';
        wsConnection = new WebSocket(wsUrl);
        wsConnection.onmessage = function (event) {
            try {
                var data = JSON.parse(event.data);
                if (data.type === 'new_alert' && data.data) {
                    alertsData.unshift(data.data);
                    if (alertsData.length > 10) alertsData.pop();
                    updateAlertsTable(alertsData);
                    // bump alert counter
                    var el = document.getElementById('active-alerts');
                    if (el) el.textContent = String(parseInt(el.textContent || '0', 10) + 1);
                }
            } catch (_) {}
        };
        wsConnection.onclose = function () { setTimeout(startWebSocketConnection, 5000); };
        wsConnection.onerror = function () {};
    } catch (_) {}
}

function startPeriodicUpdates() {
    setInterval(function () { loadSanctionsStats(); loadBlockchainStats(); loadInvestigationStats(); }, 300000);
    setInterval(function () { loadRecentAlerts(); }, 60000);
}

window.JackdawDashboard = { loadInitialData: loadInitialData };
