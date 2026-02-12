/**
 * Jackdaw Sentry Compliance Dashboard JavaScript
 * SAR reporting, regulatory compliance, and audit management — uses Auth.fetchJSON
 */

var complianceTrendChart = null;
var reportDistributionChart = null;
var sarReports = [];
var deadlines = [];

document.addEventListener('DOMContentLoaded', function () {
    if (typeof lucide !== 'undefined') lucide.createIcons();
    initializeCharts();
    loadComplianceData();
    startPeriodicUpdates();
});


function initializeCharts() {
    var c = JDS.chartColors();
    var trendEl = document.getElementById('compliance-trend-chart');
    if (trendEl) {
        complianceTrendChart = new Chart(trendEl.getContext('2d'), {
            type: 'line',
            data: { labels: JDS.lastNDaysLong(30), datasets: [{ label: 'Compliance Score', data: generateComplianceData(30), borderColor: '#22c55e', backgroundColor: 'rgba(34,197,94,0.1)', tension: 0.4, fill: true, pointRadius: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100, ticks: { color: c.text, callback: function (v) { return v + '%'; } }, grid: { color: c.grid } }, x: { ticks: { color: c.text, maxTicksLimit: 8 }, grid: { display: false } } } }
        });
    }
    var distEl = document.getElementById('report-distribution-chart');
    if (distEl) {
        reportDistributionChart = new Chart(distEl.getContext('2d'), {
            type: 'doughnut',
            data: { labels: ['SAR', 'CTR', 'CMIR', 'FBAR', 'Other'], datasets: [{ data: [45, 25, 15, 10, 5], backgroundColor: ['#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#6b21a8'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right', labels: { color: c.text, padding: 16 } } } }
        });
    }
}

async function loadComplianceData() {
    try { await Promise.all([loadSARReports(), loadComplianceMetrics(), loadRegulatoryDeadlines(), loadComplianceTimeline()]); }
    catch (_) { loadFallbackData(); }
}

async function loadSARReports() {
    try {
        var data = await Auth.fetchJSON('/api/v1/compliance/report');
        var reports = Array.isArray(data) ? data : (data && data.reports ? data.reports : []);
        sarReports = reports;
        updateSARTable(reports);
    } catch (_) {
        sarReports = fallbackSARReports();
        updateSARTable(sarReports);
    }
}

async function loadComplianceMetrics() {
    try {
        var data = await Auth.fetchJSON('/api/v1/compliance/statistics');
        if (data) {
            var score = data.compliance_score || 94.2;
            updateComplianceScore(score);
            JDS.updateStatCard('sar-count', data.total_reports || 127);
            JDS.updateStatCard('compliance-score', score.toFixed(1) + '%');
            JDS.updateStatCard('deadlines-count', data.upcoming_deadlines || 3);
            JDS.updateStatCard('audit-status', data.audit_status || 'Ready');
            if (data.pending_reports != null) { var pe = document.getElementById('sar-pending'); if (pe) pe.textContent = data.pending_reports; }
        }
    } catch (_) {
        updateComplianceScore(94.2);
        JDS.updateStatCard('sar-count', 127);
        JDS.updateStatCard('compliance-score', '94.2%');
        JDS.updateStatCard('deadlines-count', 3);
        JDS.updateStatCard('audit-status', 'Ready');
    }
}

async function loadRegulatoryDeadlines() {
    try {
        var data = await Auth.fetchJSON('/api/v1/compliance/rules');
        var items = Array.isArray(data) ? data : (data && data.rules ? data.rules : []);
        deadlines = items;
        updateDeadlinesGrid(items);
        var crit = items.filter(function (d) { return d.priority === 'critical' || d.priority === 'high'; }).length;
        var ce = document.getElementById('deadlines-critical'); if (ce) ce.textContent = crit;
    } catch (_) {
        deadlines = fallbackDeadlines();
        updateDeadlinesGrid(deadlines);
    }
}

async function loadComplianceTimeline() {
    try {
        var data = await Auth.fetchJSON('/api/v1/compliance/audit/events');
        var events = Array.isArray(data) ? data : (data && data.events ? data.events : []);
        updateComplianceTimeline(events.slice(0, 8));
    } catch (_) {
        updateComplianceTimeline(fallbackTimeline());
    }
}

function updateSARTable(reports) {
    var tbody = document.getElementById('sar-table');
    if (!tbody) return;
    tbody.innerHTML = '';
    if (!reports.length) { tbody.innerHTML = '<tr><td colspan="5" class="py-8 text-center text-slate-400">No SAR reports found</td></tr>'; return; }
    reports.slice(0, 20).forEach(function (r) { tbody.appendChild(createSARRow(r)); });
}

function createSARRow(report) {
    var row = document.createElement('tr');
    row.className = 'border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50';
    var st = report.status || 'draft';
    var stCls = { draft: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300', under_review: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300', approved: 'bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300', submitted: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300', rejected: 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300' };
    var cls = stCls[st] || stCls.draft;
    var id = report.report_id || report.id || '—';
    var tdId = document.createElement('td');
    tdId.className = 'py-3 px-4 font-medium';
    tdId.textContent = id;

    var tdType = document.createElement('td');
    tdType.className = 'py-3 px-4 text-slate-500 dark:text-slate-400';
    tdType.textContent = report.type || report.report_type || 'SAR';

    var tdStatus = document.createElement('td');
    tdStatus.className = 'py-3 px-4';
    var statusSpan = document.createElement('span');
    statusSpan.className = 'px-2 py-1 rounded-full text-xs font-semibold ' + cls;
    statusSpan.textContent = st;
    tdStatus.appendChild(statusSpan);

    var tdDate = document.createElement('td');
    tdDate.className = 'py-3 px-4 text-slate-500 dark:text-slate-400';
    tdDate.textContent = JDS.formatDate(report.due_date);

    var tdAction = document.createElement('td');
    tdAction.className = 'py-3 px-4';
    var btn = document.createElement('button');
    btn.className = 'text-blue-600 hover:text-blue-700 dark:text-blue-400 text-sm font-medium';
    btn.textContent = 'View';
    btn.addEventListener('click', function() { viewSARReport(id); });
    tdAction.appendChild(btn);

    row.appendChild(tdId);
    row.appendChild(tdType);
    row.appendChild(tdStatus);
    row.appendChild(tdDate);
    row.appendChild(tdAction);
    return row;
}

function updateComplianceScore(score) {
    var el = document.getElementById('compliance-score');
    if (el) el.textContent = score.toFixed(1) + '%';
    var bar = document.getElementById('compliance-progress-bar');
    if (bar) {
        bar.style.width = score + '%';
        bar.className = (score >= 90 ? 'bg-emerald-500' : score >= 70 ? 'bg-amber-500' : 'bg-rose-500') + ' h-2 rounded-full progress-bar';
    }
}

function updateDeadlinesGrid(items) {
    var grid = document.getElementById('deadlines-grid');
    if (!grid) return;
    grid.innerHTML = '';
    if (!items.length) { grid.innerHTML = '<p class="text-sm text-slate-400 col-span-full">No upcoming deadlines</p>'; return; }
    items.slice(0, 6).forEach(function (d) { grid.appendChild(createDeadlineCard(d)); });
}

function createDeadlineCard(d) {
    var card = document.createElement('div');
    card.className = 'p-4 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 card-hover';
    var pr = d.priority || 'normal';
    var prCls = { critical: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300', high: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300', normal: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300', low: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400' };
    var days = d.days_remaining != null ? d.days_remaining : '—';
    var esc = JDS.escapeHTML;
    card.innerHTML = '<div class="flex justify-between items-start mb-2"><div><h4 class="text-sm font-medium">' + esc(d.title || d.name || '—') + '</h4><p class="text-xs text-slate-500 dark:text-slate-400">' + esc(d.type || '—') + '</p></div><span class="px-2 py-1 text-xs font-semibold rounded-full ' + (prCls[pr] || prCls.normal) + '">' + esc(pr) + '</span></div>'
        + '<div class="space-y-1 text-sm"><div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">Due:</span><span class="font-medium">' + esc(JDS.formatDate(d.due_date)) + '</span></div>'
        + '<div class="flex justify-between"><span class="text-slate-500 dark:text-slate-400">Days left:</span><span class="font-medium">' + esc(days) + '</span></div></div>';
    return card;
}

function updateComplianceTimeline(events) {
    var el = document.getElementById('compliance-timeline');
    if (!el) return;
    el.innerHTML = '';
    if (!events.length) { el.innerHTML = '<p class="text-sm text-slate-400">No recent events</p>'; return; }
    events.forEach(function (item) {
        var div = document.createElement('div');
        div.className = 'timeline-item pb-4';
        div.innerHTML = '<h4 class="text-sm font-medium">' + (item.title || item.event_type || '—') + '</h4>'
            + '<p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">' + JDS.formatDate(item.date || item.created_at) + '</p>'
            + '<p class="text-sm text-slate-600 dark:text-slate-400 mt-1">' + (item.description || '') + '</p>';
        el.appendChild(div);
    });
}

function createSAR() {
    var id = 'SAR-' + new Date().getFullYear() + '-' + String(sarReports.length + 1).padStart(3, '0');
    var newSAR = { report_id: id, type: 'Suspicious Activity Report', status: 'draft', due_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0] };
    Auth.fetchWithAuth('/api/v1/compliance/report', { method: 'POST', body: JSON.stringify(newSAR) }).then(function () {
        sarReports.unshift(newSAR);
        updateSARTable(sarReports);
        JDS.notify('SAR created: ' + id, 'success');
    }).catch(function () {
        sarReports.unshift(newSAR);
        updateSARTable(sarReports);
        JDS.notify('SAR created locally: ' + id, 'info');
    });
}

function viewSARReport(reportId) { JDS.notify('Opening SAR: ' + reportId, 'info'); }
function handleDeadline(id) { JDS.notify('Handling deadline: ' + id, 'info'); }

function startPeriodicUpdates() {
    setInterval(function () { loadComplianceMetrics(); }, 300000);
    setInterval(function () { loadRegulatoryDeadlines(); }, 3600000);
}

function generateComplianceData(n) { var d = []; var s = 85; for (var i = 0; i < n; i++) { s += (Math.random() - 0.5) * 5; s = Math.max(80, Math.min(100, s)); d.push(+s.toFixed(1)); } return d; }


function fallbackSARReports() {
    return [
        { report_id: 'SAR-2024-001', type: 'Suspicious Activity Report', status: 'submitted', due_date: '2024-01-15' },
        { report_id: 'SAR-2024-002', type: 'Suspicious Activity Report', status: 'draft', due_date: '2024-01-20' },
        { report_id: 'SAR-2024-003', type: 'Suspicious Activity Report', status: 'under_review', due_date: '2024-01-18' },
        { report_id: 'SAR-2024-004', type: 'Currency Transaction Report', status: 'approved', due_date: '2024-01-10' }
    ];
}
function fallbackDeadlines() {
    return [
        { id: 'dl-1', type: 'SAR Report', title: 'SAR-2024-002', due_date: '2024-01-20', priority: 'high', status: 'pending', days_remaining: 5 },
        { id: 'dl-2', type: 'CTR Report', title: 'CTR-2024-001', due_date: '2024-01-25', priority: 'normal', status: 'pending', days_remaining: 10 },
        { id: 'dl-3', type: 'Annual Audit', title: '2024 Annual Compliance Audit', due_date: '2024-03-15', priority: 'normal', status: 'pending', days_remaining: 60 }
    ];
}
function fallbackTimeline() {
    return [
        { date: '2024-01-10', title: 'SAR-2024-004 Submitted', description: 'Currency Transaction Report submitted to FinCEN' },
        { date: '2024-01-08', title: 'Compliance Review Completed', description: 'Quarterly review completed with 94.2% score' },
        { date: '2024-01-05', title: 'SAR-2024-003 Created', description: 'New SAR report created for suspicious activity' }
    ];
}
function loadFallbackData() {
    sarReports = fallbackSARReports(); updateSARTable(sarReports);
    updateComplianceScore(94.2); JDS.updateStatCard('sar-count', 127); JDS.updateStatCard('compliance-score', '94.2%');
    JDS.updateStatCard('deadlines-count', 3); JDS.updateStatCard('audit-status', 'Ready');
    deadlines = fallbackDeadlines(); updateDeadlinesGrid(deadlines);
    updateComplianceTimeline(fallbackTimeline());
}

window.JackdawCompliance = { loadComplianceData: loadComplianceData, createSAR: createSAR, viewSARReport: viewSARReport, showNotification: JDS.notify };
