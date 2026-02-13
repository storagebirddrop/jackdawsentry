/**
 * Jackdaw Sentry — Graph Explorer Module (M9.3)
 * Shared Cytoscape.js wrapper used by both /graph (standalone) and /analysis (tab).
 *
 * Dependencies (loaded via CDN in consuming HTML pages):
 *   - cytoscape.js  (window.cytoscape)
 *   - cytoscape-dagre (registered as layout)
 *   - Auth module (Auth.fetchJSON)
 */

const GraphExplorer = (function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Cytoscape style sheet                                              */
    /* ------------------------------------------------------------------ */
    var STYLE = [
        {
            selector: 'node[type="address"]',
            style: {
                'label': 'data(short)',
                'text-valign': 'bottom',
                'text-halign': 'center',
                'font-size': '10px',
                'color': '#94a3b8',
                'background-color': '#3b82f6',
                'width': 36,
                'height': 36,
                'border-width': 2,
                'border-color': '#2563eb',
                'text-margin-y': 6,
            }
        },
        {
            selector: 'node[type="address"][?sanctioned]',
            style: {
                'background-color': '#ef4444',
                'border-color': '#991b1b',
                'border-width': 3,
            }
        },
        {
            selector: 'node:selected',
            style: {
                'border-color': '#facc15',
                'border-width': 3,
                'overlay-opacity': 0.08,
            }
        },
        {
            selector: 'edge',
            style: {
                'width': 2,
                'line-color': '#475569',
                'target-arrow-color': '#475569',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'arrow-scale': 0.8,
                'label': 'data(label)',
                'font-size': '8px',
                'color': '#64748b',
                'text-rotation': 'autorotate',
                'text-background-color': '#0f172a',
                'text-background-opacity': 0.7,
                'text-background-padding': '2px',
            }
        },
        {
            selector: 'edge:selected',
            style: {
                'line-color': '#facc15',
                'target-arrow-color': '#facc15',
                'width': 3,
            }
        },
    ];

    /* ------------------------------------------------------------------ */
    /* State                                                              */
    /* ------------------------------------------------------------------ */
    var _cy = null;
    var _container = null;
    var _onNodeClick = null;
    var _loading = false;

    /* ------------------------------------------------------------------ */
    /* Init                                                               */
    /* ------------------------------------------------------------------ */

    /**
     * Initialise Cytoscape on `containerEl`.
     * @param {HTMLElement} containerEl  DOM node to render into
     * @param {Object}      opts        Optional overrides
     * @param {Function}    opts.onNodeClick  callback(nodeData)
     */
    function init(containerEl, opts) {
        opts = opts || {};
        _container = containerEl;
        _onNodeClick = opts.onNodeClick || null;

        if (typeof cytoscape === 'undefined') {
            console.error('GraphExplorer: cytoscape.js not loaded');
            return false;
        }

        // Register dagre layout if available
        if (typeof cytoscapeDagre !== 'undefined' && !cytoscape._dagreRegistered) {
            cytoscape.use(cytoscapeDagre);
            cytoscape._dagreRegistered = true;
        }

        _cy = cytoscape({
            container: containerEl,
            style: STYLE,
            layout: { name: 'preset' },
            minZoom: 0.15,
            maxZoom: 4,
            wheelSensitivity: 0.3,
        });

        _cy.on('tap', 'node', function (evt) {
            var data = evt.target.data();
            if (_onNodeClick) _onNodeClick(data);
        });

        _cy.on('tap', 'edge', function (evt) {
            var data = evt.target.data();
            _showEdgeTooltip(data);
        });

        return true;
    }

    /* ------------------------------------------------------------------ */
    /* API calls                                                          */
    /* ------------------------------------------------------------------ */

    function expand(address, blockchain, opts) {
        opts = opts || {};
        _setLoading(true);
        var body = {
            address: address,
            blockchain: blockchain,
            depth: opts.depth || 1,
            direction: opts.direction || 'both',
        };
        if (opts.minValue) body.min_value = opts.minValue;

        return Auth.fetchJSON('/api/v1/graph/expand', {
            method: 'POST',
            body: JSON.stringify(body),
        }).then(function (res) {
            if (res && res.success) _mergeGraph(res.nodes, res.edges);
            return res;
        }).finally(function () { _setLoading(false); });
    }

    function trace(txHash, blockchain, opts) {
        opts = opts || {};
        _setLoading(true);
        return Auth.fetchJSON('/api/v1/graph/trace', {
            method: 'POST',
            body: JSON.stringify({
                tx_hash: txHash,
                blockchain: blockchain,
                follow_hops: opts.hops || 3,
            }),
        }).then(function (res) {
            if (res && res.success) _mergeGraph(res.nodes, res.edges);
            return res;
        }).finally(function () { _setLoading(false); });
    }

    function search(query, blockchain) {
        _setLoading(true);
        var body = { query: query };
        if (blockchain) body.blockchain = blockchain;

        return Auth.fetchJSON('/api/v1/graph/search', {
            method: 'POST',
            body: JSON.stringify(body),
        }).then(function (res) {
            if (res && res.success) {
                clear();
                _mergeGraph(res.nodes, res.edges);
            }
            return res;
        }).finally(function () { _setLoading(false); });
    }

    function summary(address, blockchain) {
        return Auth.fetchJSON(
            '/api/v1/graph/address/' + encodeURIComponent(address) + '/summary?blockchain=' + encodeURIComponent(blockchain)
        );
    }

    /* ------------------------------------------------------------------ */
    /* Graph manipulation                                                 */
    /* ------------------------------------------------------------------ */

    function _mergeGraph(nodes, edges) {
        if (!_cy) return;
        var eles = [];

        (nodes || []).forEach(function (n) {
            if (_cy.getElementById(n.id).length === 0) {
                eles.push({
                    group: 'nodes',
                    data: {
                        id: n.id,
                        type: n.type || 'address',
                        chain: n.chain || '',
                        short: _shorten(n.id),
                        balance: n.balance,
                        tx_count: n.tx_count,
                        risk: n.risk || 0,
                        sanctioned: n.sanctioned || false,
                        label: n.label || null,
                    },
                });
            }
        });

        (edges || []).forEach(function (e, i) {
            var edgeId = e.id || e.tx_hash || (e.source + '|' + e.target + '|' + (e.type || '') + '|' + (e.value || '') + '|' + i);
            if (_cy.getElementById(edgeId).length === 0 && e.source && e.target) {
                var val = parseFloat(e.value) || 0;
                eles.push({
                    group: 'edges',
                    data: {
                        id: edgeId,
                        source: e.source,
                        target: e.target,
                        value: val,
                        label: val > 0 ? _formatValue(val) : '',
                        chain: e.chain || '',
                        tx_hash: e.tx_hash || null,
                        timestamp: e.timestamp || null,
                        block_number: e.block_number || null,
                    },
                });
            }
        });

        if (eles.length > 0) {
            _cy.add(eles);
            _runLayout();
        }
    }

    function _runLayout() {
        var layoutName = 'circle';
        if (typeof cytoscapeDagre !== 'undefined') layoutName = 'dagre';

        _cy.layout({
            name: layoutName,
            animate: true,
            animationDuration: 400,
            rankDir: 'LR',
            nodeSep: 60,
            rankSep: 100,
            padding: 40,
        }).run();
    }

    function clear() {
        if (_cy) _cy.elements().remove();
    }

    function fit() {
        if (_cy) _cy.fit(undefined, 40);
    }

    function getNodeCount() {
        return _cy ? _cy.nodes().length : 0;
    }

    function getEdgeCount() {
        return _cy ? _cy.edges().length : 0;
    }

    /* ------------------------------------------------------------------ */
    /* Helpers                                                            */
    /* ------------------------------------------------------------------ */

    function _shorten(id) {
        if (!id || id.length <= 14) return id || '';
        return id.substring(0, 6) + '…' + id.substring(id.length - 4);
    }

    function _formatValue(val) {
        if (val >= 1e6) return (val / 1e6).toFixed(2) + 'M';
        if (val >= 1e3) return (val / 1e3).toFixed(2) + 'K';
        if (val >= 1) return val.toFixed(4);
        if (val >= 0.0001) return val.toFixed(6);
        return val.toExponential(2);
    }

    function _setLoading(state) {
        _loading = state;
        var el = document.getElementById('graph-loading');
        if (el) el.classList.toggle('hidden', !state);
    }

    function _showEdgeTooltip(data) {
        var el = document.getElementById('graph-edge-info');
        if (!el) return;
        el.textContent = '';
        var rows = [];
        if (data.tx_hash) rows.push(['TX', _shorten(data.tx_hash)]);
        if (data.value) rows.push(['Value', _formatValue(data.value)]);
        if (data.chain) rows.push(['Chain', String(data.chain)]);
        if (data.timestamp) rows.push(['Time', String(data.timestamp)]);
        if (data.block_number) rows.push(['Block', String(data.block_number)]);
        rows.forEach(function (r, idx) {
            if (idx > 0) el.appendChild(document.createElement('br'));
            var b = document.createElement('b');
            b.textContent = r[0] + ': ';
            el.appendChild(b);
            el.appendChild(document.createTextNode(r[1]));
        });
        el.classList.remove('hidden');
        setTimeout(function () { el.classList.add('hidden'); }, 5000);
    }

    /* ------------------------------------------------------------------ */
    /* Export PNG                                                          */
    /* ------------------------------------------------------------------ */

    function exportPNG() {
        if (!_cy) return;
        var png = _cy.png({ scale: 2, bg: '#0f172a', full: true });
        var a = document.createElement('a');
        a.href = png;
        a.download = 'jackdaw-graph-' + Date.now() + '.png';
        a.click();
    }

    /* ------------------------------------------------------------------ */
    /* Public API                                                         */
    /* ------------------------------------------------------------------ */
    return {
        init: init,
        expand: expand,
        trace: trace,
        search: search,
        summary: summary,
        clear: clear,
        fit: fit,
        exportPNG: exportPNG,
        getNodeCount: getNodeCount,
        getEdgeCount: getEdgeCount,
        isLoading: function () { return _loading; },
    };
})();
