/**
 * Jackdaw Sentry — Shared UI Utilities
 * Chart helpers, stat-card updates, date formatters, notification wrapper.
 * Depends on: nav.js (Nav.isDark)
 */

const JDS = (function () {

    /** Dark-mode-aware chart color palette */
    function chartColors() {
        var dk = Nav.isDark();
        return {
            text: dk ? '#94a3b8' : '#64748b',
            grid: dk ? '#1e293b' : '#f1f5f9',
            border: dk ? '#334155' : '#e2e8f0',
        };
    }

    /** Set an element's text by ID, optionally add fade-in */
    function updateStatCard(id, value, animate) {
        var el = document.getElementById(id);
        if (!el) return;
        el.textContent = value;
        if (animate) el.classList.add('fade-in');
    }

    /** Format an ISO date string to locale date, or '—' */
    function formatDate(s) {
        if (!s) return '—';
        return new Date(s).toLocaleDateString();
    }

    /** Relative-time formatter (Just now / X min ago / Xh ago / date) */
    function formatTime(timeString) {
        if (!timeString) return '—';
        var date = new Date(timeString);
        var diff = Date.now() - date.getTime();
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return Math.floor(diff / 60000) + ' min ago';
        if (diff < 86400000) return Math.floor(diff / 3600000) + 'h ago';
        return date.toLocaleDateString();
    }

    /** Generate last N day labels (short weekday) */
    function lastNDaysShort(n) {
        var days = [];
        var today = new Date();
        for (var i = n - 1; i >= 0; i--) {
            var d = new Date(today);
            d.setDate(d.getDate() - i);
            days.push(d.toLocaleDateString('en', { weekday: 'short' }));
        }
        return days;
    }

    /** Generate last N day labels (short month + day) */
    function lastNDaysLong(n) {
        var days = [];
        var today = new Date();
        for (var i = n - 1; i >= 0; i--) {
            var d = new Date(today);
            d.setDate(d.getDate() - i);
            days.push(d.toLocaleDateString('en', { month: 'short', day: 'numeric' }));
        }
        return days;
    }

    /**
     * Unified toast notification.
     * Delegates to Auth.showToast when available, with consistent styling.
     */
    function notify(message, type) {
        if (typeof Auth !== 'undefined' && Auth.showToast) {
            Auth.showToast(message, type || 'info');
        }
    }

    return {
        chartColors: chartColors,
        updateStatCard: updateStatCard,
        formatDate: formatDate,
        formatTime: formatTime,
        lastNDaysShort: lastNDaysShort,
        lastNDaysLong: lastNDaysLong,
        notify: notify,
    };
})();
