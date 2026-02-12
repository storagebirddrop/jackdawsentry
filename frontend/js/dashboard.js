/**
 * Jackdaw Sentry Dashboard JavaScript
 * Real-time dashboard with authenticated API calls
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

    var volumeCtx = document.getElementById('volume-chart');
    if (volumeCtx) {
        volumeChart = new Chart(volumeCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: days,
                datasets: [{
                    label: 'Transactions',
                    data: [145200, 162800, 138400, 171600, 155300, 149800, 168200],
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

    var riskCtx = document.getElementById('risk-chart');
    if (riskCtx) {
        riskChart = new Chart(riskCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Very Low', 'Low', 'Medium', 'High', 'Critical'],
                datasets: [{
                    data: [15, 25, 35, 20, 5],
                    backgroundColor: ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444', '#7f1d1d'],
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
    await Promise.all([loadDashboardStats(), loadRecentAlerts()]);
}

async function loadDashboardStats() {
    try {
        var stats = await Auth.fetchJSON('/api/v1/blockchain/statistics');
        if (stats) {
            JDS.updateStatCard('total-transactions', (stats.total_transactions || 0).toLocaleString(), true);
            JDS.updateStatCard('active-alerts', stats.active_alerts || 0, true);
            JDS.updateStatCard('avg-risk-score', (stats.avg_risk_score || 0).toFixed(2), true);
            JDS.updateStatCard('blockchains', (stats.online_blockchains || 10) + '/' + (stats.total_blockchains || 10), true);
            if (volumeChart) {
                volumeChart.data.datasets[0].data = stats.volume_data;
                volumeChart.update();
            }
            if (riskChart) {
                riskChart.data.datasets[0].data = stats.risk_distribution;
                riskChart.update();
            }
        }
    } catch (_) {
        JDS.updateStatCard('total-transactions', '1,234,567', true);
        JDS.updateStatCard('active-alerts', '23', true);
        JDS.updateStatCard('avg-risk-score', '0.67', true);
        JDS.updateStatCard('blockchains', '10/10', true);
    }
}

async function loadRecentAlerts() {
    try {
        var data = await Auth.fetchJSON('/api/v1/intelligence/alerts');
        var alerts = Array.isArray(data) ? data : (data && data.alerts ? data.alerts : []);
        alertsData = alerts.slice(0, 10);
        updateAlertsTable(alertsData);
    } catch (_) {
        var fallback = [
            { type: 'High Value Transaction', address: '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa', blockchain: 'Bitcoin', risk: 0.85, time: new Date().toISOString(), status: 'active' },
            { type: 'Sanctions Match', address: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e', blockchain: 'Ethereum', risk: 0.95, time: new Date(Date.now() - 300000).toISOString(), status: 'investigating' },
            { type: 'Mixer Usage Detected', address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh', blockchain: 'Bitcoin', risk: 0.78, time: new Date(Date.now() - 600000).toISOString(), status: 'active' }
        ];
        alertsData = fallback;
        updateAlertsTable(fallback);
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

    if (alerts.length === 0) {
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
    var risk = alert.risk || 0;
    var riskCls = risk >= 0.8 ? 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300' : risk >= 0.6 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300' : risk >= 0.4 ? 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300';
    var statusColors = { active: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300', investigating: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300', resolved: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400', pending: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300' };
    var st = alert.status || 'active';
    var stCls = statusColors[st] || statusColors.active;
    var addr = alert.address || '—';
    var shortAddr = addr.length > 16 ? addr.substring(0, 10) + '...' + addr.substring(addr.length - 6) : addr;

    var esc = JDS.escapeHTML;
    row.innerHTML = '<td class="py-3 px-4 font-medium">' + esc(alert.type || alert.alert_type || '—') + '</td>'
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
                if (data.type === 'stats_update' && data.data) {
                    JDS.updateStatCard('total-transactions', (data.data.total_transactions || 0).toLocaleString(), true);
                    JDS.updateStatCard('active-alerts', data.data.active_alerts || 0, true);
                    JDS.updateStatCard('avg-risk-score', (data.data.avg_risk_score || 0).toFixed(2), true);
                } else if (data.type === 'new_alert' && data.data) {
                    alertsData.unshift(data.data);
                    if (alertsData.length > 10) alertsData.pop();
                    updateAlertsTable(alertsData);
                }
            } catch (_) {}
        };
        wsConnection.onclose = function () { setTimeout(startWebSocketConnection, 5000); };
        wsConnection.onerror = function () {};
    } catch (_) {}
}

function startPeriodicUpdates() {
    setInterval(function () { loadDashboardStats(); }, 300000);
    setInterval(function () { loadRecentAlerts(); }, 60000);
}


function showNotification(message, type) {
    JDS.notify(message, type);
}

window.JackdawDashboard = { loadInitialData: loadInitialData, showNotification: showNotification, updateStatCard: JDS.updateStatCard };
