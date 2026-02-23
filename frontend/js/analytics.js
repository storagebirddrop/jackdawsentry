/**
 * Jackdaw Sentry — Compliance Analytics Dashboard JavaScript
 * Charts, metrics, report generation, and auto-refresh.
 * Depends on: auth.js, nav.js, utils.js
 */

var sarTrendChart, riskDistributionChart, complianceScoreChart, caseManagementChart;

document.addEventListener('DOMContentLoaded', function () {
    if (typeof lucide !== 'undefined') lucide.createIcons();
    initializeCharts();
    loadAnalyticsData();
    setupEventListeners();
    startAutoRefresh();
});

function initializeCharts() {
    var c = JDS.chartColors();

    // SAR Reports Trend Chart
    var sarCtx = document.getElementById('sarTrendChart');
    if (sarCtx) {
        sarTrendChart = new Chart(sarCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'SAR Reports',
                    data: [5, 8, 6, 9, 7, 4, 3],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { color: c.text }, grid: { color: c.grid } },
                    x: { ticks: { color: c.text }, grid: { display: false } }
                }
            }
        });
    };

    // Risk Distribution Chart
    var riskCtx = document.getElementById('riskDistributionChart');
    if (riskCtx) {
        riskDistributionChart = new Chart(riskCtx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: ['Low', 'Medium', 'High', 'Critical', 'Severe'],
                datasets: [{
                    data: [120, 85, 45, 15, 5],
                    backgroundColor: ['rgba(34,197,94,0.8)', 'rgba(245,158,11,0.8)', 'rgba(251,146,60,0.8)', 'rgba(220,38,38,0.8)', 'rgba(127,29,29,0.8)']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { color: c.text, padding: 16 } } }
            }
        });
    }

    // Compliance Score Trend Chart
    var complianceCtx = document.getElementById('complianceScoreChart');
    if (complianceCtx) {
        complianceScoreChart = new Chart(complianceCtx.getContext('2d'), {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Compliance Score',
                    data: [85, 87, 86, 89, 88, 90],
                    borderColor: '#22c55e',
                    backgroundColor: 'rgba(34, 197, 94, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: false, min: 80, max: 100, ticks: { color: c.text }, grid: { color: c.grid } },
                    x: { ticks: { color: c.text }, grid: { display: false } }
                }
            }
        });
    }

    // Case Management Chart
    var caseCtx = document.getElementById('caseManagementChart');
    if (caseCtx) {
        caseManagementChart = new Chart(caseCtx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['Open', 'In Progress', 'Under Review', 'Closed'],
                datasets: [{
                    label: 'Cases',
                    data: [12, 18, 8, 25],
                    backgroundColor: ['rgba(59,130,246,0.8)', 'rgba(245,158,11,0.8)', 'rgba(251,146,60,0.8)', 'rgba(34,197,94,0.8)']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { color: c.text }, grid: { color: c.grid } },
                    x: { ticks: { color: c.text }, grid: { display: false } }
                }
            }
        });
    }
}

async function loadAnalyticsData() {
    try {
        var data = await Auth.fetchJSON('/api/v1/compliance/analytics/dashboard');
        if (data) {
            updateDashboard(data);
        }
    } catch (error) {
        console.error('Failed to load analytics data:', error);
        updateDashboardWithMockData();
    }
}

function updateDashboard(data) {
    if (data.overview) {
        JDS.updateStatCard('sarCount', data.overview.total_sar_reports);
        JDS.updateStatCard('activeCases', data.overview.active_cases);
        JDS.updateStatCard('complianceScore', data.overview.compliance_score + '%');
        JDS.updateStatCard('riskScore', data.overview.average_risk_score.toFixed(2));
    }

    if (data.trends) {
        updateCharts(data.trends);
    }

    if (data.alerts) {
        updateAlerts(data.alerts);
    }

    if (data.performance) {
        updatePerformanceMetrics(data.performance);
    }

    if (data.insights) {
        var container = document.getElementById('insightsContainer');
        if (container) {
            container.innerHTML = '';
            data.insights.forEach(function (text) {
                var card = document.createElement('div');
                card.className = 'insight-card p-4 rounded';
                card.innerHTML = '<p class="text-sm text-slate-600 dark:text-slate-300">\u2022 ' + text + '</p>';
                container.appendChild(card);
            });
        }
    }

    if (data.recommendations) {
        var container = document.getElementById('recommendationsContainer');
        if (container) {
            container.innerHTML = '';
            data.recommendations.forEach(function (text) {
                var card = document.createElement('div');
                card.className = 'recommendation-card p-4 rounded';
                card.innerHTML = '<p class="text-sm text-slate-600 dark:text-slate-300">\u2022 ' + text + '</p>';
                container.appendChild(card);
            });
        }
    }
}

function updateDashboardWithMockData() {
    console.log('Using mock data for dashboard');
}

function updateCharts(trends) {
    if (trends.sar_reports_trend && sarTrendChart) {
        sarTrendChart.data.datasets[0].data = trends.sar_reports_trend;
        sarTrendChart.update();
    }
}

function updateAlerts(alerts) {
    var alertsContainer = document.getElementById('alertsContainer');
    if (alertsContainer && alerts) {
        var alertCards = alertsContainer.querySelectorAll('.alert-card');
        if (alertCards[0]) {
            alertCards[0].querySelector('.text-xs').textContent = alerts.high_risk_cases + ' cases require attention';
        }
        if (alertCards[1]) {
            alertCards[1].querySelector('.text-xs').textContent = alerts.upcoming_deadlines + ' deadlines in next 7 days';
        }
        if (alertCards[2]) {
            alertCards[2].querySelector('.text-xs').textContent = alerts.overdue_reports + ' reports past deadline';
        }
    }
}

function updatePerformanceMetrics(performance) {
    if (performance.processing_time != null) {
        var el = document.getElementById('perfProcessingTime');
        if (el) el.textContent = performance.processing_time.toFixed(1) + ' min';
    }
    if (performance.processing_delta != null) {
        var el = document.getElementById('perfProcessingDelta');
        if (el) el.textContent = (performance.processing_delta > 0 ? '+' : '') + performance.processing_delta + '% improvement';
    }
    if (performance.processing_pct != null) {
        var el = document.getElementById('perfProcessingBar');
        if (el) el.style.width = Math.min(100, performance.processing_pct) + '%';
    }
    if (performance.system_health != null) {
        var el = document.getElementById('perfSystemHealth');
        if (el) el.textContent = performance.system_health.toFixed(1) + '%';
        var bar = document.getElementById('perfSystemHealthBar');
        if (bar) bar.style.width = Math.min(100, performance.system_health) + '%';
        var label = document.getElementById('perfSystemHealthLabel');
        if (label) label.textContent = performance.system_health >= 90 ? 'Excellent' : performance.system_health >= 70 ? 'Good' : 'Needs Attention';
    }
    if (performance.user_satisfaction != null) {
        var el = document.getElementById('perfUserSatisfaction');
        if (el) el.textContent = performance.user_satisfaction.toFixed(1) + '%';
        var bar = document.getElementById('perfUserSatisfactionBar');
        if (bar) bar.style.width = Math.min(100, performance.user_satisfaction) + '%';
    }
    if (performance.user_satisfaction_delta != null) {
        var el = document.getElementById('perfUserSatisfactionDelta');
        if (el) el.textContent = (performance.user_satisfaction_delta > 0 ? '+' : '') + performance.user_satisfaction_delta + '% this month';
    }
}

function setupEventListeners() {
    var periodEl = document.getElementById('reportPeriod');
    if (periodEl) {
        periodEl.addEventListener('change', function () {
            loadAnalyticsData();
        });
    }

    window.generateReport = function () {
        var period = document.getElementById('reportPeriod').value;
        generateAnalyticsReport(period);
    };
}

async function generateAnalyticsReport(period) {
    try {
        var report = await Auth.fetchJSON('/api/v1/compliance/analytics/report', {
            method: 'POST',
            body: JSON.stringify({
                report_type: period,
                period_start: getPeriodStart(period),
                period_end: new Date().toISOString()
            })
        });
        if (report) {
            showReportModal(report);
        } else {
            throw new Error('Failed to generate report');
        }
    } catch (error) {
        console.error('Failed to generate report:', error);
        JDS.notify('Failed to generate report. Please try again.', 'error');
    }
}

function getPeriodStart(period) {
    var now = new Date();
    var ms;
    switch (period) {
        case 'daily':     ms = 24 * 60 * 60 * 1000; break;
        case 'weekly':    ms = 7 * 24 * 60 * 60 * 1000; break;
        case 'monthly':   ms = 30 * 24 * 60 * 60 * 1000; break;
        case 'quarterly': ms = 90 * 24 * 60 * 60 * 1000; break;
        case 'annual':    ms = 365 * 24 * 60 * 60 * 1000; break;
        default:          ms = 7 * 24 * 60 * 60 * 1000;
    }
    return new Date(now.getTime() - ms).toISOString();
}

function showReportModal(report) {
    var modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black/50 overflow-y-auto h-full w-full z-50';
    modal.setAttribute('role', 'dialog');
    modal.setAttribute('aria-modal', 'true');
    modal.setAttribute('aria-label', report.title);
    modal.setAttribute('tabindex', '-1');

    var metricsHtml = '';
    if (report.metrics) {
        metricsHtml = report.metrics.map(function (m) {
            return '<div class="bg-slate-50 dark:bg-slate-800 p-3 rounded">'
                + '<p class="text-sm font-medium text-slate-900 dark:text-white">' + m.name + '</p>'
                + '<p class="text-lg font-bold text-slate-900 dark:text-white">' + m.value + ' ' + m.unit + '</p>'
                + '</div>';
        }).join('');
    }

    var insightsHtml = '';
    if (report.insights) {
        insightsHtml = report.insights.map(function (i) {
            return '<li class="text-sm text-slate-600 dark:text-slate-300">' + i + '</li>';
        }).join('');
    }

    var recsHtml = '';
    if (report.recommendations) {
        recsHtml = report.recommendations.map(function (r) {
            return '<li class="text-sm text-slate-600 dark:text-slate-300">' + r + '</li>';
        }).join('');
    }

    modal.innerHTML = ''
        + '<div class="relative top-20 mx-auto p-4 border border-slate-200 dark:border-slate-700 w-11/12 max-w-2xl shadow-lg rounded-md bg-white dark:bg-slate-900">'
        + '  <div class="flex justify-between items-center mb-4">'
        + '    <h3 class="text-lg font-medium text-slate-900 dark:text-white">' + report.title + '</h3>'
        + '    <button data-modal-close class="text-slate-400 hover:text-slate-500 dark:text-slate-400 dark:hover:text-slate-300" aria-label="Close dialog">'
        + '      <i data-lucide="x" class="w-6 h-6"></i>'
        + '    </button>'
        + '  </div>'
        + '  <div class="mb-4">'
        + '    <p class="text-sm text-slate-500 dark:text-slate-400">' + report.description + '</p>'
        + '    <p class="text-xs text-slate-400 dark:text-slate-500 mt-2">Generated: ' + new Date(report.generated_at).toLocaleString() + '</p>'
        + '  </div>'
        + '  <div class="mb-4">'
        + '    <h4 class="font-medium text-slate-900 dark:text-white mb-2">Key Metrics</h4>'
        + '    <div class="grid grid-cols-2 gap-4">' + metricsHtml + '</div>'
        + '  </div>'
        + '  <div class="mb-4">'
        + '    <h4 class="font-medium text-slate-900 dark:text-white mb-2">Insights</h4>'
        + '    <ul class="list-disc list-inside space-y-1">' + insightsHtml + '</ul>'
        + '  </div>'
        + '  <div class="mb-4">'
        + '    <h4 class="font-medium text-slate-900 dark:text-white mb-2">Recommendations</h4>'
        + '    <ul class="list-disc list-inside space-y-1">' + recsHtml + '</ul>'
        + '  </div>'
        + '  <div class="flex justify-end">'
        + '    <button data-modal-download class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">Download Report</button>'
        + '  </div>'
        + '</div>';

    document.body.appendChild(modal);
    if (typeof lucide !== 'undefined') lucide.createIcons();

    function removeModal() {
        document.removeEventListener('keydown', onKeyDown);
        modal.remove();
    }

    var closeBtn = modal.querySelector('[data-modal-close]');
    if (closeBtn) closeBtn.addEventListener('click', removeModal);

    var dlBtn = modal.querySelector('[data-modal-download]');
    if (dlBtn) dlBtn.addEventListener('click', function () { downloadReport(report.report_id); });

    modal.addEventListener('click', function (e) {
        if (e.target === modal) removeModal();
    });

    function onKeyDown(e) {
        if (e.key === 'Escape') { removeModal(); return; }
        if (e.key === 'Tab') {
            var focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
            if (focusable.length === 0) return;
            var first = focusable[0];
            var last = focusable[focusable.length - 1];
            if (e.shiftKey) {
                if (document.activeElement === first) { e.preventDefault(); last.focus(); }
            } else {
                if (document.activeElement === last) { e.preventDefault(); first.focus(); }
            }
        }
    }
    document.addEventListener('keydown', onKeyDown);
    if (closeBtn) closeBtn.focus();
}

function downloadReport(reportId) {
    window.open('/api/v1/compliance/analytics/download/' + reportId, '_blank');
}

// Visibility-aware auto-refresh (every 5 minutes)
var refreshInterval = null;
function startAutoRefresh() {
    if (!refreshInterval) {
        refreshInterval = setInterval(loadAnalyticsData, 5 * 60 * 1000);
    }
}
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}
document.addEventListener('visibilitychange', function () {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        loadAnalyticsData();
        startAutoRefresh();
    }
});
