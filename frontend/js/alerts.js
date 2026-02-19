/**
 * Jackdaw Sentry — Live Alert Feed (M12)
 *
 * Connects to the WebSocket alert stream and renders incoming alerts
 * as toast notifications and entries in the alert feed table.
 *
 * Usage: include this script on any page that should show live alerts.
 * Requires auth.js (for getToken / fetchWithAuth).
 */

(function () {
  "use strict";

  const WS_PATH = "/api/v1/alerts/ws";
  const RECONNECT_DELAY_MS = 5000;
  const MAX_FEED_ROWS = 100;

  const SEVERITY_COLORS = {
    critical: "#ef4444",
    high:     "#f97316",
    medium:   "#eab308",
    low:      "#22c55e",
  };

  let _ws = null;
  let _reconnectTimer = null;
  let _feedBody = null;
  let _alertCount = 0;

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  window.AlertFeed = {
    /** Start the WebSocket connection and render into #alert-feed-body if present. */
    start() {
      _feedBody = document.getElementById("alert-feed-body");
      _connect();
    },

    /** Gracefully close the connection. */
    stop() {
      if (_reconnectTimer) {
        clearTimeout(_reconnectTimer);
        _reconnectTimer = null;
      }
      if (_ws) {
        _ws.close(1000, "User navigated away");
        _ws = null;
      }
    },
  };

  // ---------------------------------------------------------------------------
  // WebSocket lifecycle
  // ---------------------------------------------------------------------------

  function _connect() {
    const token = (window.getToken && window.getToken()) || localStorage.getItem("token");
    if (!token) {
      console.warn("[AlertFeed] No auth token — live alerts disabled");
      return;
    }

    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}${WS_PATH}`;

    _ws = new WebSocket(url);

    _ws.onopen = () => {
      console.log("[AlertFeed] Connected");
      // Send JWT for WebSocket auth
      _ws.send(JSON.stringify({ token }));
    };

    _ws.onmessage = (event) => {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch {
        return;
      }

      if (data.status === "authenticated") {
        console.log("[AlertFeed] Authenticated — streaming alerts");
        return;
      }

      _handleAlert(data);
    };

    _ws.onclose = (event) => {
      if (event.code !== 1000) {
        console.warn(`[AlertFeed] Disconnected (${event.code}) — reconnecting in ${RECONNECT_DELAY_MS / 1000}s`);
        _reconnectTimer = setTimeout(_connect, RECONNECT_DELAY_MS);
      }
    };

    _ws.onerror = (err) => {
      console.error("[AlertFeed] WebSocket error", err);
    };
  }

  // ---------------------------------------------------------------------------
  // Alert rendering
  // ---------------------------------------------------------------------------

  function _handleAlert(alert) {
    _alertCount++;
    _showToast(alert);
    if (_feedBody) {
      _prependFeedRow(alert);
    }
    _updateBadge(_alertCount);
  }

  function _showToast(alert) {
    const color = SEVERITY_COLORS[alert.severity] || "#6b7280";
    const toast = document.createElement("div");
    toast.style.cssText = `
      position: fixed; bottom: 1.5rem; right: 1.5rem; z-index: 9999;
      background: #1f2937; color: #f9fafb; border-left: 4px solid ${color};
      padding: 0.75rem 1.25rem; border-radius: 0.5rem;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4); min-width: 280px;
      font-size: 0.875rem; transition: opacity 0.3s;
    `;
    toast.innerHTML = `
      <div style="font-weight:600; margin-bottom:0.25rem;">
        🚨 Alert: ${_esc(alert.rule_name || "Unknown rule")}
        <span style="font-size:0.75rem; color:${color}; margin-left:0.5rem;">[${_esc(alert.severity)}]</span>
      </div>
      <div style="color:#9ca3af;">${_esc(alert.detail || "")}</div>
      <div style="color:#6b7280; font-size:0.75rem; margin-top:0.25rem;">
        ${alert.transaction_hash ? `tx: ${_esc(alert.transaction_hash.slice(0, 16))}…` : ""}
        ${alert.blockchain ? `· ${_esc(alert.blockchain)}` : ""}
      </div>
    `;

    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      setTimeout(() => toast.remove(), 300);
    }, 6000);
  }

  function _prependFeedRow(alert) {
    const color = SEVERITY_COLORS[alert.severity] || "#6b7280";
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="px-3 py-2 text-xs text-gray-400">${_fmtTime(alert.fired_at)}</td>
      <td class="px-3 py-2 font-medium">${_esc(alert.rule_name || "—")}</td>
      <td class="px-3 py-2">
        <span style="color:${color}; font-weight:600;">${_esc(alert.severity)}</span>
      </td>
      <td class="px-3 py-2 text-gray-400 text-xs truncate max-w-xs">${_esc(alert.detail || "—")}</td>
      <td class="px-3 py-2 text-xs font-mono text-gray-500">
        ${alert.transaction_hash ? _esc(alert.transaction_hash.slice(0, 16)) + "…" : "—"}
      </td>
    `;
    _feedBody.prepend(tr);

    // Trim old rows
    while (_feedBody.children.length > MAX_FEED_ROWS) {
      _feedBody.removeChild(_feedBody.lastChild);
    }
  }

  function _updateBadge(count) {
    const badge = document.getElementById("alert-badge");
    if (badge) {
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.style.display = "inline-flex";
    }
  }

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  function _esc(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function _fmtTime(iso) {
    try {
      return new Date(iso).toLocaleTimeString();
    } catch {
      return iso || "—";
    }
  }
})();
