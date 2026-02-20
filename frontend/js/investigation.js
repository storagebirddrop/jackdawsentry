/**
 * Jackdaw Sentry — Investigation Detail Page (M17)
 *
 * IIFE module for /investigation?id=X
 * Requires: auth.js, nav.js, utils.js, graph.js
 */
const InvestigationDetail = (function () {
    'use strict';

    var _invId = new URLSearchParams(location.search).get('id');
    var _inv = null;
    var _narrativeDebounce = null;
    var _notesDebounce = null;

    // -------------------------------------------------------------------------
    // Init
    // -------------------------------------------------------------------------

    function init() {
        if (!_invId) {
            document.getElementById('inv-content').innerHTML =
                '<p class="text-slate-400 p-8">No investigation ID provided.</p>';
            return;
        }
        setupTabs();
        loadInvestigation();
        setupSidebar();
    }

    // -------------------------------------------------------------------------
    // Tabs
    // -------------------------------------------------------------------------

    function setupTabs() {
        var tabs = document.querySelectorAll('[data-tab]');
        tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                var target = tab.dataset.tab;
                tabs.forEach(function (t) {
                    t.classList.remove('border-blue-600', 'text-blue-600', 'dark:text-blue-400', 'dark:border-blue-500');
                    t.classList.add('border-transparent', 'text-slate-500');
                });
                tab.classList.remove('border-transparent', 'text-slate-500');
                tab.classList.add('border-blue-600', 'text-blue-600', 'dark:text-blue-400', 'dark:border-blue-500');
                document.querySelectorAll('[data-panel]').forEach(function (p) {
                    p.classList.add('hidden');
                });
                var panel = document.getElementById('panel-' + target);
                if (panel) panel.classList.remove('hidden');

                if (target === 'evidence') loadEvidence();
                if (target === 'timeline') loadTimeline();
                if (target === 'graph') loadGraph();
                if (target === 'narrative') { /* loaded on button click */ }
            });
        });
        // Activate first tab
        if (tabs.length) tabs[0].click();
    }

    // -------------------------------------------------------------------------
    // Core data load
    // -------------------------------------------------------------------------

    async function loadInvestigation() {
        try {
            _inv = await Auth.fetchJSON('/api/v1/investigations/' + _invId);
            renderHeader(_inv);
            renderOverview(_inv);
            renderSidebar(_inv);
        } catch (err) {
            console.error('Failed to load investigation:', err);
        }
    }

    function renderHeader(inv) {
        var esc = JDS.escapeHTML;
        document.getElementById('inv-title-text').textContent = inv.title || 'Investigation #' + _invId;
        document.getElementById('inv-id-badge').textContent = '#' + _invId;

        var pr = inv.priority || 'medium';
        var prCls = { low: 'bg-slate-100 text-slate-700', medium: 'bg-blue-100 text-blue-700', high: 'bg-amber-100 text-amber-700', critical: 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' };
        var badge = document.getElementById('inv-priority-badge');
        badge.textContent = pr.charAt(0).toUpperCase() + pr.slice(1);
        badge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold ' + (prCls[pr] || prCls.medium);

        var statusSel = document.getElementById('inv-status-select');
        if (statusSel) statusSel.value = inv.status || 'open';
    }

    function renderOverview(inv) {
        var esc = JDS.escapeHTML;
        document.getElementById('ov-created').textContent = inv.created_at ? new Date(inv.created_at).toLocaleString() : '—';
        document.getElementById('ov-assigned').textContent = inv.assigned_to || '—';
        document.getElementById('ov-type').textContent = inv.investigation_type ? inv.investigation_type.replace(/_/g, ' ') : '—';
        document.getElementById('ov-tags').textContent = (inv.tags || []).join(', ') || '—';

        var notes = document.getElementById('ov-notes');
        if (notes) notes.value = inv.notes || '';
    }

    // -------------------------------------------------------------------------
    // Evidence tab
    // -------------------------------------------------------------------------

    async function loadEvidence(type) {
        var tbody = document.getElementById('evidence-tbody');
        if (!tbody) return;
        tbody.innerHTML = '<tr><td colspan="4" class="py-6 text-center text-slate-400">Loading…</td></tr>';
        try {
            var url = '/api/v1/investigations/' + _invId + '/evidence';
            if (type && type !== 'all') url += '?evidence_type=' + encodeURIComponent(type);
            var data = await Auth.fetchJSON(url);
            var items = Array.isArray(data) ? data : (data && data.evidence ? data.evidence : []);
            if (!items.length) {
                tbody.innerHTML = '<tr><td colspan="4" class="py-6 text-center text-slate-400">No evidence items</td></tr>';
                return;
            }
            var esc = JDS.escapeHTML;
            tbody.innerHTML = items.map(function (ev) {
                var conf = ev.confidence != null ? (ev.confidence * 100).toFixed(0) + '%' : '—';
                return '<tr class="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/40">'
                    + '<td class="py-2 px-4 text-xs font-mono text-slate-500">' + esc(ev.id || '—') + '</td>'
                    + '<td class="py-2 px-4"><span class="px-2 py-0.5 rounded text-xs bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">' + esc(ev.evidence_type || '—') + '</span></td>'
                    + '<td class="py-2 px-4 text-sm">' + esc(ev.description || '—') + '</td>'
                    + '<td class="py-2 px-4 text-sm text-slate-500">' + conf + '</td>'
                    + '</tr>';
            }).join('');
        } catch (err) {
            tbody.innerHTML = '<tr><td colspan="4" class="py-6 text-center text-slate-400">Failed to load evidence</td></tr>';
        }
    }

    async function addEvidence(type, description, data, confidence) {
        await Auth.fetchWithAuth('/api/v1/investigations/evidence', {
            method: 'POST',
            body: JSON.stringify({
                investigation_id: _invId,
                evidence_type: type,
                description: description,
                data: data || {},
                confidence: parseFloat(confidence) || 0.8
            })
        });
        loadEvidence();
    }

    // -------------------------------------------------------------------------
    // Timeline tab
    // -------------------------------------------------------------------------

    async function loadTimeline() {
        var container = document.getElementById('timeline-container');
        if (!container) return;
        container.innerHTML = '<p class="text-slate-400 text-sm p-4">Loading…</p>';
        try {
            var data = await Auth.fetchJSON('/api/v1/investigations/' + _invId + '/timeline');
            var events = Array.isArray(data) ? data : (data && data.events ? data.events : []);
            if (!events.length) {
                container.innerHTML = '<p class="text-slate-400 text-sm p-4">No timeline events</p>';
                return;
            }
            var esc = JDS.escapeHTML;
            container.innerHTML = '<div class="relative pl-6 border-l-2 border-slate-200 dark:border-slate-700 space-y-6">'
                + events.map(function (ev) {
                    return '<div class="relative">'
                        + '<div class="absolute -left-[1.625rem] top-1 w-3 h-3 rounded-full bg-blue-500 border-2 border-white dark:border-slate-900"></div>'
                        + '<p class="text-xs text-slate-400 mb-0.5">' + (ev.timestamp ? new Date(ev.timestamp).toLocaleString() : '—') + '</p>'
                        + '<p class="text-sm font-medium">' + esc(ev.event_type || ev.type || '—') + '</p>'
                        + '<p class="text-xs text-slate-500 mt-0.5">' + esc(ev.description || '') + '</p>'
                        + '</div>';
                }).join('')
                + '</div>';
        } catch (err) {
            container.innerHTML = '<p class="text-slate-400 text-sm p-4">Failed to load timeline</p>';
        }
    }

    // -------------------------------------------------------------------------
    // Graph tab
    // -------------------------------------------------------------------------

    function loadGraph() {
        var canvas = document.getElementById('inv-graph-canvas');
        if (!canvas || typeof GraphExplorer === 'undefined') return;
        if (!canvas._graphInit) {
            GraphExplorer.init(canvas, {
                onNodeClick: function (data) {
                    updateGraphStats();
                }
            });
            canvas._graphInit = true;
        }
        GraphExplorer.loadGraphFromInvestigation(_invId)
            .then(function () { updateGraphStats(); })
            .catch(function (err) { console.warn('No saved graph:', err); });
        loadAnnotations();
    }

    function updateGraphStats() {
        var el = document.getElementById('inv-graph-stats');
        if (el) el.textContent = (GraphExplorer.getNodeCount() + ' nodes · ' + GraphExplorer.getEdgeCount() + ' edges');
    }

    async function loadAnnotations() {
        var list = document.getElementById('annotations-list');
        if (!list) return;
        try {
            var data = await Auth.fetchJSON('/api/v1/investigations/' + _invId + '/graph/annotations');
            var anns = Array.isArray(data) ? data : (data && data.annotations ? data.annotations : []);
            if (!anns.length) { list.innerHTML = '<p class="text-xs text-slate-400">No annotations</p>'; return; }
            var esc = JDS.escapeHTML;
            list.innerHTML = anns.map(function (a) {
                return '<div class="flex items-start gap-2 text-xs border-b border-slate-100 dark:border-slate-800 py-2">'
                    + '<span class="px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 shrink-0">' + esc(a.annotation_type || 'note') + '</span>'
                    + '<span class="flex-1 text-slate-600 dark:text-slate-300">' + esc(a.content || '') + '</span>'
                    + '<button onclick="InvestigationDetail.deleteAnnotation(\'' + esc(a.id) + '\')" class="text-slate-300 hover:text-rose-500 shrink-0">&times;</button>'
                    + '</div>';
            }).join('');
        } catch (_) {}
    }

    async function addAnnotation(targetId, type, content) {
        await Auth.fetchWithAuth('/api/v1/investigations/' + _invId + '/graph/annotations', {
            method: 'POST',
            body: JSON.stringify({ target_id: targetId, annotation_type: type, content: content })
        });
        loadAnnotations();
    }

    async function deleteAnnotation(annId) {
        if (!confirm('Delete this annotation?')) return;
        await Auth.fetchWithAuth('/api/v1/investigations/' + _invId + '/graph/annotations/' + annId, { method: 'DELETE' });
        loadAnnotations();
    }

    // -------------------------------------------------------------------------
    // Narrative tab
    // -------------------------------------------------------------------------

    async function generateNarrative() {
        var btn = document.getElementById('btn-generate-narrative');
        var out = document.getElementById('narrative-output');
        if (!out) return;
        btn.disabled = true;
        btn.textContent = 'Generating…';
        out.innerHTML = '<div class="animate-pulse text-slate-400 text-sm">Generating narrative…</div>';
        try {
            var data = await Auth.fetchJSON('/api/v1/investigations/' + _invId + '/narrative', { method: 'POST' });
            var text = data && (data.narrative || data.text || JSON.stringify(data));
            out.innerHTML = '<div class="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap">' + JDS.escapeHTML(text) + '</div>';
        } catch (err) {
            out.innerHTML = '<p class="text-rose-500 text-sm">Failed to generate narrative: ' + JDS.escapeHTML(String(err)) + '</p>';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Generate Narrative';
        }
    }

    async function exportPDF() {
        try {
            var resp = await Auth.fetchWithAuth('/api/v1/investigations/' + _invId + '/report/pdf');
            var blob = await resp.blob();
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url;
            a.download = 'investigation-' + _invId + '.pdf';
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            alert('PDF export failed: ' + err);
        }
    }

    // -------------------------------------------------------------------------
    // Status / notes save
    // -------------------------------------------------------------------------

    async function saveStatus(status) {
        try {
            await Auth.fetchWithAuth('/api/v1/investigations/' + _invId, {
                method: 'PUT',
                body: JSON.stringify({ status: status })
            });
        } catch (err) {
            console.error('Failed to save status:', err);
        }
    }

    function scheduleSaveNotes(notes) {
        if (_notesDebounce) clearTimeout(_notesDebounce);
        _notesDebounce = setTimeout(async function () {
            try {
                await Auth.fetchWithAuth('/api/v1/investigations/' + _invId, {
                    method: 'PUT',
                    body: JSON.stringify({ notes: notes })
                });
            } catch (_) {}
        }, 800);
    }

    // -------------------------------------------------------------------------
    // Sidebar
    // -------------------------------------------------------------------------

    function setupSidebar() {
        // Wired via inline HTML events
    }

    function renderSidebar(inv) {
        var el = document.getElementById('sb-assigned');
        if (el) el.textContent = inv.assigned_to || '—';
        var tags = document.getElementById('sb-tags');
        if (tags) tags.textContent = (inv.tags || []).join(', ') || '—';
        var prSel = document.getElementById('sb-priority-select');
        if (prSel) prSel.value = inv.priority || 'medium';
        var stSel = document.getElementById('sb-status-select');
        if (stSel) stSel.value = inv.status || 'open';
    }

    async function saveSidebar() {
        var priority = document.getElementById('sb-priority-select').value;
        var status = document.getElementById('sb-status-select').value;
        var assigned = document.getElementById('sb-assigned-input').value;
        var tagsRaw = document.getElementById('sb-tags-input').value;
        var tags = tagsRaw ? tagsRaw.split(',').map(function (t) { return t.trim(); }) : [];
        try {
            await Auth.fetchWithAuth('/api/v1/investigations/' + _invId, {
                method: 'PUT',
                body: JSON.stringify({ priority: priority, status: status, assigned_to: assigned || undefined, tags: tags })
            });
            loadInvestigation();
        } catch (err) {
            alert('Save failed: ' + err);
        }
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    return {
        init: init,
        generateNarrative: generateNarrative,
        exportPDF: exportPDF,
        deleteAnnotation: deleteAnnotation,
        addAnnotation: addAnnotation,
        addEvidence: addEvidence,
        saveStatus: saveStatus,
        scheduleSaveNotes: scheduleSaveNotes,
        saveSidebar: saveSidebar,
        updateGraphStats: updateGraphStats,
        loadEvidence: loadEvidence,
    };
})();

document.addEventListener('DOMContentLoaded', InvestigationDetail.init);
