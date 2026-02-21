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
            selector: 'node[entity_name]',
            style: {
                'label': 'data(entity_name)',
                'font-weight': 'bold',
            }
        },
        {
            selector: 'node[entity_type="exchange"]',
            style: {
                'background-color': '#22c55e',
                'border-color': '#15803d',
            }
        },
        {
            selector: 'node[entity_type="mixer"]',
            style: {
                'background-color': '#f97316',
                'border-color': '#c2410c',
            }
        },
        {
            selector: 'node[entity_type="darknet_market"]',
            style: {
                'background-color': '#ef4444',
                'border-color': '#991b1b',
            }
        },
        {
            selector: 'node[entity_type="defi_protocol"]',
            style: {
                'background-color': '#a855f7',
                'border-color': '#7e22ce',
            }
        },
        {
            selector: 'node[entity_type="scam"]',
            style: {
                'background-color': '#ef4444',
                'border-color': '#7f1d1d',
                'border-style': 'dashed',
            }
        },
        {
            selector: 'node[entity_type="bridge"]',
            style: {
                'background-color': '#06b6d4',
                'border-color': '#0e7490',
            }
        },
        {
            selector: 'node[entity_type="mining_pool"]',
            style: {
                'background-color': '#eab308',
                'border-color': '#a16207',
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
        // Colored edges by edge_type
        {
            selector: 'edge[edge_type="bridge"]',
            style: {
                'line-color': '#f97316',         // orange
                'target-arrow-color': '#f97316',
                'width': 2.5,
            }
        },
        {
            selector: 'edge[edge_type="dex"]',
            style: {
                'line-color': '#a855f7',          // purple
                'target-arrow-color': '#a855f7',
                'width': 2,
            }
        },
        {
            selector: 'edge[edge_type="mixer"]',
            style: {
                'line-color': '#ef4444',          // red
                'target-arrow-color': '#ef4444',
                'width': 3,
                'line-style': 'dashed',
            }
        },
        // Compound parent style for clustered addresses
        {
            selector: ':parent',
            style: {
                'background-opacity': 0.1,
                'border-color': '#64748b',
                'border-width': 1,
                'label': 'data(cluster_label)',
                'font-size': '9px',
                'color': '#94a3b8',
                'text-valign': 'top',
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
    var _allEdges = [];          // cache for timeline filtering

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
            var node = evt.target;
            var data = Object.assign({}, node.data());
            // Collect adjacent edge TxIDs for display in Node Detail
            var inTxIds = [], outTxIds = [];
            node.connectedEdges().forEach(function (e) {
                var txid = e.data('tx_hash');
                if (!txid) return;
                if (e.data('target') === data.id && inTxIds.indexOf(txid) < 0) inTxIds.push(txid);
                if (e.data('source') === data.id && outTxIds.indexOf(txid) < 0) outTxIds.push(txid);
            });
            data._inTxIds  = inTxIds;
            data._outTxIds = outTxIds;
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
                        entity_name: n.entity_name || null,
                        entity_type: n.entity_type || null,
                        entity_category: n.entity_category || null,
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
                        edge_type: e.edge_type || 'transfer',
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
        _allEdges = [];
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
        if (!id || id.length <= 10) return id || '';
        return id.substring(0, 4) + '…' + id.substring(id.length - 4);
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
        el.innerHTML = '';

        // Header row with dismiss button
        var header = document.createElement('div');
        header.className = 'flex items-center justify-between mb-2';
        var title = document.createElement('span');
        title.className = 'font-semibold text-slate-200 text-xs uppercase tracking-wide';
        title.textContent = 'Transaction';
        var closeBtn = document.createElement('button');
        closeBtn.textContent = '×';
        closeBtn.className = 'ml-3 text-slate-400 hover:text-white text-sm leading-none';
        closeBtn.onclick = function () { el.classList.add('hidden'); };
        header.appendChild(title);
        header.appendChild(closeBtn);
        el.appendChild(header);

        var rows = [];
        if (data.tx_hash) rows.push(['TxID', data.tx_hash, true]);   // full hash, copyable
        if (data.value)   rows.push(['Value', _formatValue(data.value) + ' BTC']);
        if (data.chain)   rows.push(['Chain', String(data.chain)]);
        if (data.timestamp) rows.push(['Time',  String(data.timestamp).replace('T', ' ').replace(/\.\d+Z$/, ' UTC')]);
        if (data.block_number) rows.push(['Block', String(data.block_number)]);

        rows.forEach(function (r) {
            var row = document.createElement('div');
            row.className = 'flex items-start gap-1 mt-1';
            var label = document.createElement('span');
            label.className = 'text-slate-400 w-10 flex-shrink-0';
            label.textContent = r[0];
            var val = document.createElement('span');
            val.className = 'text-slate-200 break-all font-mono text-xs';
            val.textContent = r[1];
            row.appendChild(label);
            row.appendChild(val);
            // Copy button for TxID
            if (r[2]) {
                var copyBtn = document.createElement('button');
                copyBtn.className = 'ml-1 text-slate-500 hover:text-blue-400 flex-shrink-0';
                copyBtn.title = 'Copy TxID';
                copyBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>';
                copyBtn.onclick = function () {
                    navigator.clipboard.writeText(r[1]).then(function () {
                        copyBtn.innerHTML = '✓';
                        setTimeout(function () {
                            copyBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>';
                        }, 1500);
                    });
                };
                row.appendChild(copyBtn);
            }
            el.appendChild(row);
        });

        el.classList.remove('hidden');
        // Don't auto-hide — user dismisses with ×
    }

    /* ------------------------------------------------------------------ */
    /* Timeline slider filter                                              */
    /* ------------------------------------------------------------------ */

    /**
     * Filter edges by timestamp range using a slider value.
     * @param {number} fromTs  Unix timestamp (seconds) – edges with ts < fromTs are hidden
     * @param {number} toTs    Unix timestamp (seconds) – edges with ts > toTs are hidden (0 = no limit)
     */
    function filterByTimeRange(fromTs, toTs) {
        if (!_cy) return;
        _cy.edges().forEach(function (edge) {
            var ts = edge.data('timestamp');
            if (!ts) {
                edge.style('display', 'element');
                return;
            }
            var edgeMs = new Date(ts).getTime() / 1000;
            var visible = edgeMs >= fromTs && (toTs === 0 || edgeMs <= toTs);
            edge.style('display', visible ? 'element' : 'none');
        });
    }

    /* ------------------------------------------------------------------ */
    /* Investigation graph persistence                                     */
    /* ------------------------------------------------------------------ */

    function saveGraphToInvestigation(investigationId) {
        if (!_cy) return Promise.reject(new Error('Graph not initialised'));
        var nodes = _cy.nodes().map(function (n) { return n.data(); });
        var edges = _cy.edges().map(function (e) { return e.data(); });
        var layout = {};
        _cy.nodes().forEach(function (n) {
            var pos = n.position();
            layout[n.id()] = { x: pos.x, y: pos.y };
        });
        return Auth.fetchJSON('/api/v1/investigations/' + investigationId + '/graph', {
            method: 'PUT',
            body: JSON.stringify({ nodes: nodes, edges: edges, layout: layout }),
        });
    }

    function loadGraphFromInvestigation(investigationId) {
        return Auth.fetchJSON('/api/v1/investigations/' + investigationId + '/graph')
            .then(function (res) {
                if (res && res.graph_state) {
                    var state = res.graph_state;
                    clear();
                    _mergeGraph(state.nodes || [], state.edges || []);
                    // Restore positions if layout is present
                    var layout = state.layout || {};
                    Object.keys(layout).forEach(function (nodeId) {
                        var node = _cy.getElementById(nodeId);
                        if (node.length) node.position(layout[nodeId]);
                    });
                }
                return res;
            });
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
        filterByTimeRange: filterByTimeRange,
        saveGraphToInvestigation: saveGraphToInvestigation,
        loadGraphFromInvestigation: loadGraphFromInvestigation,
        resize: function () { if (_cy) { _cy.resize(); _cy.fit(); } },
    };
})();
