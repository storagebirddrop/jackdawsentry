/**
 * Jackdaw Sentry Compliance Dashboard JavaScript
 * SAR reporting, regulatory compliance, and audit management
 */

// Global variables
let complianceTrendChart = null;
let reportDistributionChart = null;
let sarReports = [];
let deadlines = [];

// Initialize compliance dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    loadComplianceData();
    setupEventListeners();
    startPeriodicUpdates();
});

/**
 * Initialize charts
 */
function initializeCharts() {
    // Compliance Score Trend Chart
    const trendCtx = document.getElementById('compliance-trend-chart').getContext('2d');
    complianceTrendChart = new Chart(trendCtx, {
        type: 'line',
        data: {
            labels: getLast30Days(),
            datasets: [{
                label: 'Compliance Score',
                data: generateComplianceData(30),
                borderColor: 'rgb(34, 197, 94)',
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });

    // Report Distribution Chart
    const distributionCtx = document.getElementById('report-distribution-chart').getContext('2d');
    reportDistributionChart = new Chart(distributionCtx, {
        type: 'doughnut',
        data: {
            labels: ['SAR', 'CTR', 'CMIR', 'FBAR', 'Other'],
            datasets: [{
                data: [45, 25, 15, 10, 5],
                backgroundColor: [
                    'rgba(30, 64, 175, 0.8)',
                    'rgba(124, 58, 237, 0.8)',
                    'rgba(217, 119, 6, 0.8)',
                    'rgba(220, 38, 38, 0.8)',
                    'rgba(107, 33, 168, 0.8)'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

/**
 * Load compliance data
 */
async function loadComplianceData() {
    try {
        // Load SAR reports
        await loadSARReports();
        
        // Load compliance metrics
        await loadComplianceMetrics();
        
        // Load regulatory deadlines
        await loadRegulatoryDeadlines();
        
        // Load compliance timeline
        await loadComplianceTimeline();
        
    } catch (error) {
        console.error('Error loading compliance data:', error);
        showNotification('Error loading compliance data', 'error');
        // Use fallback data
        loadFallbackData();
    }
}

/**
 * Load SAR reports
 */
async function loadSARReports() {
    try {
        const response = await fetch('/api/v1/compliance/sar/reports');
        const reports = await response.json();
        
        sarReports = reports;
        updateSARTable(reports);
        
    } catch (error) {
        console.error('Error loading SAR reports:', error);
        // Use fallback data
        const fallbackReports = [
            {
                report_id: 'SAR-2024-001',
                type: 'Suspicious Activity Report',
                status: 'submitted',
                due_date: '2024-01-15',
                created_at: '2024-01-01T10:00:00Z',
                amount: 125000,
                currency: 'USD',
                jurisdiction: 'USA'
            },
            {
                report_id: 'SAR-2024-002',
                type: 'Suspicious Activity Report',
                status: 'draft',
                due_date: '2024-01-20',
                created_at: '2024-01-05T14:30:00Z',
                amount: 75000,
                currency: 'USD',
                jurisdiction: 'USA'
            },
            {
                report_id: 'SAR-2024-003',
                type: 'Suspicious Activity Report',
                status: 'under_review',
                due_date: '2024-01-18',
                created_at: '2024-01-08T09:15:00Z',
                amount: 250000,
                currency: 'USD',
                jurisdiction: 'USA'
            },
            {
                report_id: 'SAR-2024-004',
                type: 'Currency Transaction Report',
                status: 'approved',
                due_date: '2024-01-10',
                created_at: '2024-01-02T16:45:00Z',
                amount: 15000,
                currency: 'USD',
                jurisdiction: 'USA'
            }
        ];
        
        sarReports = fallbackReports;
        updateSARTable(fallbackReports);
    }
}

/**
 * Load compliance metrics
 */
async function loadComplianceMetrics() {
    try {
        const response = await fetch('/api/v1/compliance/metrics');
        const metrics = await response.json();
        
        // Update compliance score
        updateComplianceScore(metrics.compliance_score);
        
        // Update stats cards
        updateStatCard('sar-count', metrics.total_sar_reports);
        updateStatCard('compliance-score', metrics.compliance_score.toFixed(1) + '%');
        updateStatCard('deadlines-count', metrics.upcoming_deadlines);
        updateStatCard('audit-status', metrics.audit_status);
        
        // Update charts
        updateCharts(metrics);
        
    } catch (error) {
        console.error('Error loading compliance metrics:', error);
        // Use fallback metrics
        const fallbackMetrics = {
            compliance_score: 94.2,
            total_sar_reports: 127,
            upcoming_deadlines: 3,
            audit_status: 'Ready',
            score_trend: generateComplianceData(30),
            report_distribution: [45, 25, 15, 10, 5]
        };
        
        updateComplianceScore(fallbackMetrics.compliance_score);
        updateStatCard('sar-count', fallbackMetrics.total_sar_reports);
        updateStatCard('compliance-score', fallbackMetrics.compliance_score.toFixed(1) + '%');
        updateStatCard('deadlines-count', fallbackMetrics.upcoming_deadlines);
        updateStatCard('audit-status', fallbackMetrics.audit_status);
        updateCharts(fallbackMetrics);
    }
}

/**
 * Load regulatory deadlines
 */
async function loadRegulatoryDeadlines() {
    try {
        const response = await fetch('/api/v1/compliance/deadlines');
        const deadlineData = await response.json();
        
        deadlines = deadlineData;
        updateDeadlinesGrid(deadlines);
        
    } catch (error) {
        console.error('Error loading deadlines:', error);
        // Use fallback data
        const fallbackDeadlines = [
            {
                id: 'deadline-1',
                type: 'SAR Report',
                title: 'SAR-2024-002',
                due_date: '2024-01-20',
                priority: 'high',
                status: 'pending',
                days_remaining: 5
            },
            {
                id: 'deadline-2',
                type: 'CTR Report',
                title: 'CTR-2024-001',
                due_date: '2024-01-25',
                priority: 'normal',
                status: 'pending',
                days_remaining: 10
            },
            {
                id: 'deadline-3',
                type: 'Annual Audit',
                title: '2024 Annual Compliance Audit',
                due_date: '2024-03-15',
                priority: 'normal',
                status: 'pending',
                days_remaining: 60
            }
        ];
        
        deadlines = fallbackDeadlines;
        updateDeadlinesGrid(fallbackDeadlines);
    }
}

/**
 * Load compliance timeline
 */
async function loadComplianceTimeline() {
    try {
        const response = await fetch('/api/v1/compliance/timeline');
        const timelineData = await response.json();
        
        updateComplianceTimeline(timelineData);
        
    } catch (error) {
        console.error('Error loading timeline:', error);
        // Use fallback data
        const fallbackTimeline = [
            {
                date: '2024-01-10',
                title: 'SAR-2024-004 Submitted',
                description: 'Currency Transaction Report submitted to FinCEN',
                type: 'submission'
            },
            {
                date: '2024-01-08',
                title: 'Compliance Review Completed',
                description: 'Quarterly compliance review completed with 94.2% score',
                type: 'review'
            },
            {
                date: '2024-01-05',
                title: 'SAR-2024-003 Created',
                description: 'New SAR report created for suspicious activity',
                type: 'creation'
            },
            {
                date: '2024-01-01',
                title: 'New Year Compliance Plan',
                description: '2024 compliance plan approved and implemented',
                type: 'milestone'
            }
        ];
        
        updateComplianceTimeline(fallbackTimeline);
    }
}

/**
 * Update SAR table
 */
function updateSARTable(reports) {
    const tableBody = document.getElementById('sar-table');
    tableBody.innerHTML = '';
    
    reports.forEach(report => {
        const row = createSARRow(report);
        tableBody.appendChild(row);
    });
}

/**
 * Create SAR row
 */
function createSARRow(report) {
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-50 fade-in';
    
    const statusBadge = getStatusBadge(report.status);
    const dueDateClass = getDueDateClass(report.due_date);
    
    row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
            ${report.report_id}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${report.type}
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
            ${statusBadge}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            <span class="${dueDateClass}">${formatDate(report.due_date)}</span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
            <button onclick="viewSARReport('${report.report_id}')" class="text-primary hover:text-primary-600">
                View
            </button>
            <button onclick="editSARReport('${report.report_id}')" class="ml-2 text-gray-600 hover:text-gray-900">
                Edit
            </button>
        </td>
    `;
    
    return row;
}

/**
 * Update compliance score
 */
function updateComplianceScore(score) {
    const scoreElement = document.getElementById('compliance-score');
    if (scoreElement) {
        scoreElement.textContent = score.toFixed(1) + '%';
        
        // Update progress bar
        const progressBar = scoreElement.closest('.compliance-card').querySelector('.progress-bar');
        if (progressBar) {
            progressBar.style.width = score + '%';
            
            // Update color based on score
            if (score >= 90) {
                progressBar.className = 'bg-success h-2 rounded-full progress-bar';
            } else if (score >= 70) {
                progressBar.className = 'bg-warning h-2 rounded-full progress-bar';
            } else {
                progressBar.className = 'bg-danger h-2 rounded-full progress-bar';
            }
        }
    }
}

/**
 * Update deadlines grid
 */
function updateDeadlinesGrid(deadlines) {
    const grid = document.getElementById('deadlines-grid');
    grid.innerHTML = '';
    
    deadlines.forEach(deadline => {
        const card = createDeadlineCard(deadline);
        grid.appendChild(card);
    });
}

/**
 * Create deadline card
 */
function createDeadlineCard(deadline) {
    const card = document.createElement('div');
    card.className = 'bg-white p-4 rounded-lg border border-gray-200 compliance-card';
    
    const priorityColor = getPriorityColor(deadline.priority);
    const daysClass = getDaysClass(deadline.days_remaining);
    
    card.innerHTML = `
        <div class="flex justify-between items-start mb-2">
            <div>
                <h4 class="text-sm font-medium text-gray-900">${deadline.title}</h4>
                <p class="text-xs text-gray-500">${deadline.type}</p>
            </div>
            <span class="px-2 py-1 text-xs font-semibold rounded-full ${priorityColor}">
                ${deadline.priority}
            </span>
        </div>
        <div class="space-y-2">
            <div class="flex justify-between text-sm">
                <span class="text-gray-500">Due Date:</span>
                <span class="font-medium">${formatDate(deadline.due_date)}</span>
            </div>
            <div class="flex justify-between text-sm">
                <span class="text-gray-500">Days Left:</span>
                <span class="font-medium ${daysClass}">${deadline.days_remaining}</span>
            </div>
            <div class="flex justify-between text-sm">
                <span class="text-gray-500">Status:</span>
                <span class="font-medium">${deadline.status}</span>
            </div>
        </div>
        <div class="mt-3">
            <button onclick="handleDeadline('${deadline.id}')" class="w-full bg-primary text-white px-3 py-2 rounded text-sm font-medium hover:bg-primary-600">
                Handle
            </button>
        </div>
    `;
    
    return card;
}

/**
 * Update compliance timeline
 */
function updateComplianceTimeline(timeline) {
    const timelineContainer = document.getElementById('compliance-timeline');
    timelineContainer.innerHTML = '';
    
    timeline.forEach((item, index) => {
        const timelineItem = createTimelineItem(item, index);
        timelineContainer.appendChild(timelineItem);
    });
}

/**
 * Create timeline item
 */
function createTimelineItem(item, index) {
    const timelineItem = document.createElement('div');
    timelineItem.className = 'timeline-item fade-in';
    
    const typeIcon = getTypeIcon(item.type);
    const typeColor = getTypeColor(item.type);
    
    timelineItem.innerHTML = `
        <div class="flex items-start">
            <div class="flex-shrink-0">
                <div class="flex items-center justify-center w-8 h-8 rounded-full ${typeColor}">
                    ${typeIcon}
                </div>
            </div>
            <div class="ml-4">
                <div class="flex items-center">
                    <h4 class="text-sm font-medium text-gray-900">${item.title}</h4>
                    <span class="ml-2 text-xs text-gray-500">${formatDate(item.date)}</span>
                </div>
                <p class="mt-1 text-sm text-gray-600">${item.description}</p>
            </div>
        </div>
    `;
    
    return timelineItem;
}

/**
 * Update charts with new data
 */
function updateCharts(metrics) {
    if (complianceTrendChart && metrics.score_trend) {
        complianceTrendChart.data.datasets[0].data = metrics.score_trend;
        complianceTrendChart.update();
    }
    
    if (reportDistributionChart && metrics.report_distribution) {
        reportDistributionChart.data.datasets[0].data = metrics.report_distribution;
        reportDistributionChart.update();
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Create SAR button
    document.querySelector('button[onclick*="Create New SAR"]')?.addEventListener('click', createNewSAR);
    
    // Navigation
    document.querySelectorAll('nav a').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            if (href && href !== '#') {
                window.location.href = href;
            }
        });
    });
}

/**
 * Create new SAR
 */
async function createNewSAR() {
    try {
        // This would open a modal or navigate to SAR creation page
        showNotification('Opening SAR creation form...', 'info');
        
        // For now, simulate creating a new SAR
        const newSAR = {
            report_id: 'SAR-' + new Date().getFullYear() + '-' + String(sarReports.length + 1).padStart(3, '0'),
            type: 'Suspicious Activity Report',
            status: 'draft',
            due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
            created_at: new Date().toISOString(),
            amount: 0,
            currency: 'USD',
            jurisdiction: 'USA'
        };
        
        sarReports.unshift(newSAR);
        updateSARTable(sarReports);
        
        // Update stats
        const currentCount = parseInt(document.getElementById('sar-count').textContent);
        updateStatCard('sar-count', currentCount + 1);
        
        showNotification('New SAR report created: ' + newSAR.report_id, 'success');
        
    } catch (error) {
        console.error('Error creating SAR:', error);
        showNotification('Error creating SAR report', 'error');
    }
}

/**
 * View SAR report
 */
function viewSARReport(reportId) {
    showNotification(`Opening SAR report: ${reportId}`, 'info');
    // This would open the SAR report details modal or page
}

/**
 * Edit SAR report
 */
function editSARReport(reportId) {
    showNotification(`Opening SAR editor: ${reportId}`, 'info');
    // This would open the SAR edit modal or page
}

/**
 * Handle deadline
 */
function handleDeadline(deadlineId) {
    const deadline = deadlines.find(d => d.id === deadlineId);
    if (deadline) {
        showNotification(`Handling deadline: ${deadline.title}`, 'info');
        // This would open the deadline handling modal or page
    }
}

/**
 * Start periodic updates
 */
function startPeriodicUpdates() {
    // Update compliance metrics every 5 minutes
    setInterval(() => {
        loadComplianceMetrics();
    }, 300000);
    
    // Update deadlines every hour
    setInterval(() => {
        loadRegulatoryDeadlines();
    }, 3600000);
    
    // Update timeline every 6 hours
    setInterval(() => {
        loadComplianceTimeline();
    }, 21600000);
}

/**
 * Helper functions
 */
function getStatusBadge(status) {
    const badges = {
        draft: 'bg-gray-100 text-gray-800',
        under_review: 'bg-yellow-100 text-yellow-800',
        approved: 'bg-blue-100 text-blue-800',
        submitted: 'bg-green-100 text-green-800',
        acknowledged: 'bg-green-100 text-green-800',
        rejected: 'bg-red-100 text-red-800',
        archived: 'bg-gray-100 text-gray-800'
    };
    
    const color = badges[status] || 'bg-gray-100 text-gray-800';
    return `<span class="px-2 py-1 text-xs font-semibold rounded-full ${color}">${status}</span>`;
}

function getDueDateClass(dueDate) {
    const due = new Date(dueDate);
    const now = new Date();
    const daysUntilDue = Math.ceil((due - now) / (1000 * 60 * 60 * 24));
    
    if (daysUntilDue < 0) return 'text-red-600';
    if (daysUntilDue <= 3) return 'text-orange-600';
    if (daysUntilDue <= 7) return 'text-yellow-600';
    return 'text-gray-600';
}

function getPriorityColor(priority) {
    const colors = {
        critical: 'bg-red-100 text-red-800',
        high: 'bg-orange-100 text-orange-800',
        normal: 'bg-blue-100 text-blue-800',
        low: 'bg-gray-100 text-gray-800'
    };
    
    return colors[priority] || 'bg-gray-100 text-gray-800';
}

function getDaysClass(days) {
    if (days < 0) return 'text-red-600 font-bold';
    if (days <= 3) return 'text-orange-600 font-bold';
    if (days <= 7) return 'text-yellow-600';
    return 'text-gray-600';
}

function getTypeIcon(type) {
    const icons = {
        submission: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        review: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2H9a2 2 0 00-2-2V5z"></path></svg>',
        creation: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0V6m0 6h6m-6 0h6"></path></svg>',
        milestone: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002 2v-6a2 2 0 00-2-2H9z"></path></svg>'
    };
    
    return icons[type] || icons.creation;
}

function getTypeColor(type) {
    const colors = {
        submission: 'bg-green-100 text-green-600',
        review: 'bg-blue-100 text-blue-600',
        creation: 'bg-purple-100 text-purple-600',
        milestone: 'bg-yellow-100 text-yellow-600'
    };
    
    return colors[type] || 'bg-gray-100 text-gray-600';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function getLast30Days() {
    const days = [];
    const today = new Date();
    
    for (let i = 29; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        days.push(date.toLocaleDateString());
    }
    
    return days;
}

function generateComplianceData(days) {
    const data = [];
    let score = 85; // Starting score
    
    for (let i = 0; i < days; i++) {
        // Simulate score variations
        score += (Math.random() - 0.5) * 5;
        score = Math.max(80, Math.min(100, score)); // Keep between 80-100
        data.push(score);
    }
    
    return data;
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 px-4 py-3 rounded-lg shadow-lg z-50 fade-in ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        type === 'warning' ? 'bg-yellow-500 text-white' :
        'bg-blue-500 text-white'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

/**
 * Update stat card
 */
function updateStatCard(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
        element.classList.add('fade-in');
    }
}

/**
 * Load fallback data
 */
function loadFallbackData() {
    const fallbackReports = [
        {
            report_id: 'SAR-2024-001',
            type: 'Suspicious Activity Report',
            status: 'submitted',
            due_date: '2024-01-15',
            created_at: '2024-01-01T10:00:00Z',
            amount: 125000,
            currency: 'USD',
            jurisdiction: 'USA'
        },
        {
            report_id: 'SAR-2024-002',
            type: 'Suspicious Activity Report',
            status: 'draft',
            due_date: '2024-01-20',
            created_at: '2024-01-05T14:30:00Z',
            amount: 75000,
            currency: 'USD',
            jurisdiction: 'USA'
        }
    ];
    
    sarReports = fallbackReports;
    updateSARTable(fallbackReports);
    
    const fallbackMetrics = {
        compliance_score: 94.2,
        total_sar_reports: 127,
        upcoming_deadlines: 3,
        audit_status: 'Ready'
    };
    
    updateComplianceScore(fallbackMetrics.compliance_score);
    updateStatCard('sar-count', fallbackMetrics.total_sar_reports);
    updateStatCard('compliance-score', fallbackMetrics.compliance_score.toFixed(1) + '%');
    updateStatCard('deadlines-count', fallbackMetrics.upcoming_deadlines);
    updateStatCard('audit-status', fallbackMetrics.audit_status);
    updateCharts(fallbackMetrics);
    
    const fallbackDeadlines = [
        {
            id: 'deadline-1',
            type: 'SAR Report',
            title: 'SAR-2024-002',
            due_date: '2024-01-20',
            priority: 'high',
            status: 'pending',
            days_remaining: 5
        }
    ];
    
    deadlines = fallbackDeadlines;
    updateDeadlinesGrid(fallbackDeadlines);
    
    const fallbackTimeline = [
        {
            date: '2024-01-10',
            title: 'SAR-2024-004 Submitted',
            description: 'Currency Transaction Report submitted to FinCEN',
            type: 'submission'
        },
        {
            date: '2024-01-08',
            title: 'Compliance Review Completed',
            description: 'Quarterly compliance review completed with 94.2% score',
            type: 'review'
        }
    ];
    
    updateComplianceTimeline(fallbackTimeline);
}

/**
 * Export functions for use in other files
 */
window.JackdawCompliance = {
    loadComplianceData,
    loadSARReports,
    createNewSAR,
    viewSARReport,
    editSARReport,
    showNotification
};
