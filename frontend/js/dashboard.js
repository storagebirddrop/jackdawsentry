/**
 * Jackdaw Sentry Dashboard JavaScript
 * Real-time dashboard functionality with charts and live updates
 */

// Global variables
let volumeChart = null;
let riskChart = null;
let alertsData = [];
let wsConnection = null;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
    loadInitialData();
    startWebSocketConnection();
    setupEventListeners();
    startPeriodicUpdates();
});

/**
 * Initialize charts
 */
function initializeCharts() {
    // Transaction Volume Chart
    const volumeCtx = document.getElementById('volume-chart').getContext('2d');
    volumeChart = new Chart(volumeCtx, {
        type: 'line',
        data: {
            labels: getLast7Days(),
            datasets: [{
                label: 'Transactions',
                data: generateRandomData(7, 100000, 200000),
                borderColor: 'rgb(30, 64, 175)',
                backgroundColor: 'rgba(30, 64, 175, 0.1)',
                tension: 0.4
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
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            }
        }
    });

    // Risk Distribution Chart
    const riskCtx = document.getElementById('risk-chart').getContext('2d');
    riskChart = new Chart(riskCtx, {
        type: 'doughnut',
        data: {
            labels: ['Very Low', 'Low', 'Medium', 'High', 'Very High'],
            datasets: [{
                data: [15, 25, 35, 20, 5],
                backgroundColor: [
                    'rgba(34, 197, 94, 0.8)',
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(251, 191, 36, 0.8)',
                    'rgba(239, 68, 68, 0.8)',
                    'rgba(127, 29, 29, 0.8)'
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
 * Load initial data
 */
async function loadInitialData() {
    try {
        // Load dashboard statistics
        await loadDashboardStats();
        
        // Load recent alerts
        await loadRecentAlerts();
        
        // Load blockchain status
        await loadBlockchainStatus();
        
    } catch (error) {
        console.error('Error loading initial data:', error);
        showNotification('Error loading dashboard data', 'error');
    }
}

/**
 * Load dashboard statistics
 */
async function loadDashboardStats() {
    try {
        const response = await fetch('/api/v1/dashboard/stats');
        const stats = await response.json();
        
        // Update stats cards
        updateStatCard('total-transactions', stats.total_transactions.toLocaleString());
        updateStatCard('active-alerts', stats.active_alerts);
        updateStatCard('avg-risk-score', stats.avg_risk_score.toFixed(2));
        updateStatCard('blockchains', `${stats.online_blockchains}/${stats.total_blockchains}`);
        
    } catch (error) {
        console.error('Error loading stats:', error);
        // Use fallback data
        updateStatCard('total-transactions', '1,234,567');
        updateStatCard('active-alerts', '23');
        updateStatCard('avg-risk-score', '0.67');
        updateStatCard('blockchains', '10/10');
    }
}

/**
 * Load recent alerts
 */
async function loadRecentAlerts() {
    try {
        const response = await fetch('/api/v1/alerts/recent?limit=10');
        const alerts = await response.json();
        
        alertsData = alerts;
        updateAlertsTable(alerts);
        
    } catch (error) {
        console.error('Error loading alerts:', error);
        // Use fallback data
        const fallbackAlerts = [
            {
                type: 'High Value Transaction',
                address: '1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa',
                blockchain: 'Bitcoin',
                risk: 0.85,
                time: new Date().toISOString(),
                status: 'active'
            },
            {
                type: 'Sanctions Match',
                address: '0x742d35Cc6634C0532925a3b844Bc454e4438f44e',
                blockchain: 'Ethereum',
                risk: 0.95,
                time: new Date(Date.now() - 300000).toISOString(),
                status: 'investigating'
            },
            {
                type: 'Mixer Usage Detected',
                address: 'bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                blockchain: 'Bitcoin',
                risk: 0.78,
                time: new Date(Date.now() - 600000).toISOString(),
                status: 'active'
            }
        ];
        
        alertsData = fallbackAlerts;
        updateAlertsTable(fallbackAlerts);
    }
}

/**
 * Load blockchain status
 */
async function loadBlockchainStatus() {
    try {
        const response = await fetch('/api/v1/blockchain/status');
        const status = await response.json();
        
        // Update blockchain status indicators
        updateBlockchainStatus(status);
        
    } catch (error) {
        console.error('Error loading blockchain status:', error);
        // Use fallback data
        const fallbackStatus = {
            bitcoin: { status: 'online', last_block: 825432, transactions: 12345 },
            ethereum: { status: 'online', last_block: 18543210, transactions: 54321 },
            bsc: { status: 'online', last_block: 32454321, transactions: 23456 },
            polygon: { status: 'online', last_block: 54321098, transactions: 18765 },
            arbitrum: { status: 'online', last_block: 12345678, transactions: 9876 },
            base: { status: 'online', last_block: 9876543, transactions: 6543 },
            avalanche: { status: 'online', last_block: 45678901, transactions: 4321 },
            solana: { status: 'online', last_block: 234567890, transactions: 32109 },
            tron: { status: 'online', last_block: 56789012, transactions: 21098 },
            lightning: { status: 'online', channels: 8765, capacity: 1234.56 }
        };
        
        updateBlockchainStatus(fallbackStatus);
    }
}

/**
 * Update alerts table
 */
function updateAlertsTable(alerts) {
    const tableBody = document.getElementById('alerts-table');

    // Remove loading row
    const loadingRow = tableBody.querySelector('.alerts-loading');
    if (loadingRow) loadingRow.remove();

    // Handle empty-state row
    let emptyRow = tableBody.querySelector('.alerts-empty');
    if (!emptyRow) {
        // Re-create if it was cleared
        emptyRow = document.createElement('tr');
        emptyRow.className = 'alerts-empty hidden';
        emptyRow.innerHTML = '<td colspan="6" class="px-6 py-8 text-center text-sm text-gray-400">No alerts found</td>';
        tableBody.appendChild(emptyRow);
    }

    // Clear all data rows (keep only the empty-state row)
    Array.from(tableBody.querySelectorAll('tr:not(.alerts-empty)')).forEach(r => r.remove());

    if (alerts.length === 0) {
        emptyRow.classList.remove('hidden');
    } else {
        emptyRow.classList.add('hidden');
        alerts.forEach(alert => {
            const row = createAlertRow(alert);
            tableBody.insertBefore(row, emptyRow);
        });
    }
}

/**
 * Create alert row
 */
function createAlertRow(alert) {
    const row = document.createElement('tr');
    row.className = 'hover:bg-gray-50 fade-in';
    
    const riskColor = getRiskColor(alert.risk);
    const statusBadge = getStatusBadge(alert.status);
    
    row.innerHTML = `
        <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
            ${alert.type}
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            <span class="font-mono">${alert.address.substring(0, 10)}...${alert.address.substring(alert.address.length - 6)}</span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${alert.blockchain}
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${riskColor}">
                ${(alert.risk * 100).toFixed(0)}%
            </span>
        </td>
        <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${formatTime(alert.time)}
        </td>
        <td class="px-6 py-4 whitespace-nowrap">
            ${statusBadge}
        </td>
    `;
    
    return row;
}

/**
 * Get risk color class
 */
function getRiskColor(risk) {
    if (risk >= 0.8) return 'bg-red-100 text-red-800';
    if (risk >= 0.6) return 'bg-yellow-100 text-yellow-800';
    if (risk >= 0.4) return 'bg-blue-100 text-blue-800';
    return 'bg-green-100 text-green-800';
}

/**
 * Get status badge HTML
 */
function getStatusBadge(status) {
    const colors = {
        active: 'bg-green-100 text-green-800',
        investigating: 'bg-yellow-100 text-yellow-800',
        resolved: 'bg-gray-100 text-gray-800',
        pending: 'bg-blue-100 text-blue-800'
    };
    
    const color = colors[status] || 'bg-gray-100 text-gray-800';
    return `<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${color}">${status}</span>`;
}

/**
 * Format time
 */
function formatTime(timeString) {
    const date = new Date(timeString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    return date.toLocaleDateString();
}

/**
 * Update stat card
 */
function updateStatCard(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
        element.parentElement.classList.add('fade-in');
    }
}

/**
 * Update blockchain status
 */
function updateBlockchainStatus(status) {
    // This would update blockchain status indicators
    console.log('Blockchain status:', status);
}

/**
 * Start WebSocket connection for real-time updates
 */
function startWebSocketConnection() {
    try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`;
        
        wsConnection = new WebSocket(wsUrl);
        
        wsConnection.onopen = function() {
            console.log('WebSocket connected');
            showNotification('Real-time updates connected', 'success');
        };
        
        wsConnection.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        };
        
        wsConnection.onclose = function() {
            console.log('WebSocket disconnected');
            showNotification('Real-time updates disconnected', 'warning');
            // Attempt to reconnect after 5 seconds
            setTimeout(startWebSocketConnection, 5000);
        };
        
        wsConnection.onerror = function(error) {
            console.error('WebSocket error:', error);
        };
        
    } catch (error) {
        console.error('Error starting WebSocket:', error);
        // Fallback to polling
        startPolling();
    }
}

/**
 * Handle WebSocket messages
 */
function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'stats_update':
            updateStats(data.data);
            break;
        case 'new_alert':
            addNewAlert(data.data);
            break;
        case 'blockchain_status':
            updateBlockchainStatus(data.data);
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

/**
 * Update stats from WebSocket
 */
function updateStats(data) {
    updateStatCard('total-transactions', data.total_transactions.toLocaleString());
    updateStatCard('active-alerts', data.active_alerts);
    updateStatCard('avg-risk-score', data.avg_risk_score.toFixed(2));
    
    // Update charts
    updateCharts(data);
}

/**
 * Add new alert from WebSocket
 */
function addNewAlert(alert) {
    alertsData.unshift(alert);
    if (alertsData.length > 10) {
        alertsData.pop();
    }
    updateAlertsTable(alertsData);
    
    // Show notification
    showNotification(`New ${alert.type} alert detected`, 'warning');
}

/**
 * Update charts with new data
 */
function updateCharts(data) {
    if (volumeChart && data.volume_data) {
        volumeChart.data.datasets[0].data = data.volume_data;
        volumeChart.update();
    }
    
    if (riskChart && data.risk_distribution) {
        riskChart.data.datasets[0].data = data.risk_distribution;
        riskChart.update();
    }
}

/**
 * Start polling as fallback
 */
function startPolling() {
    setInterval(async () => {
        await loadDashboardStats();
        await loadRecentAlerts();
    }, 30000); // Poll every 30 seconds
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Navigation
    document.querySelectorAll('nav a').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            if (href.startsWith('#')) {
                loadSection(href.substring(1));
            }
        });
    });
    
    // Refresh button
    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'fixed bottom-4 right-4 bg-primary text-white px-4 py-2 rounded-lg shadow-lg hover:bg-primary-600';
    refreshBtn.innerHTML = 'Refresh';
    refreshBtn.onclick = loadInitialData;
    document.body.appendChild(refreshBtn);
}

/**
 * Load section
 */
function loadSection(section) {
    console.log('Loading section:', section);
    // This would load different sections of the application
    showNotification(`Loading ${section}...`, 'info');
}

/**
 * Start periodic updates
 */
function startPeriodicUpdates() {
    // Update charts every minute
    setInterval(() => {
        if (volumeChart) {
            volumeChart.data.datasets[0].data = generateRandomData(7, 100000, 200000);
            volumeChart.update();
        }
    }, 60000);
    
    // Update stats every 5 minutes
    setInterval(() => {
        loadDashboardStats();
    }, 300000);
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
 * Get last 7 days
 */
function getLast7Days() {
    const days = [];
    const today = new Date();
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        days.push(date.toLocaleDateString());
    }
    
    return days;
}

/**
 * Generate random data for demo
 */
function generateRandomData(count, min, max) {
    const data = [];
    for (let i = 0; i < count; i++) {
        data.push(Math.floor(Math.random() * (max - min + 1)) + min);
    }
    return data;
}

/**
 * Export functions for use in other files
 */
window.JackdawDashboard = {
    loadInitialData,
    loadDashboardStats,
    loadRecentAlerts,
    showNotification,
    updateStatCard
};
