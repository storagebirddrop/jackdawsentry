/**
 * Jackdaw Sentry — "Add to Investigation" Modal (M17)
 *
 * Shared IIFE component for analysis.html and graph.html.
 * Usage:
 *   InvestigationModal.show({
 *     evidence_type: 'address_analysis',
 *     description: 'High risk address detected',
 *     data: { address, blockchain, risk_score, patterns },
 *     confidence: 0.9,
 *     _onConfirm: function(invId) { ... }   // optional callback
 *   });
 */
const InvestigationModal = (function () {
    'use strict';

    var _evidence = null;
    var _modal = null;

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    function show(evidence) {
        _evidence = evidence || {};
        _ensureModal();
        _loadInvestigations();
        document.getElementById('inv-modal-overlay').classList.remove('hidden');
    }

    function hide() {
        var overlay = document.getElementById('inv-modal-overlay');
        if (overlay) overlay.classList.add('hidden');
    }

    // -------------------------------------------------------------------------
    // Modal HTML
    // -------------------------------------------------------------------------

    function _ensureModal() {
        if (document.getElementById('inv-modal-overlay')) return;
        var el = document.createElement('div');
        el.id = 'inv-modal-overlay';
        el.className = 'hidden fixed inset-0 z-50 flex items-center justify-center bg-black/60';
        el.innerHTML = [
            '<div class="bg-white dark:bg-slate-900 rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 w-full max-w-lg mx-4">',
            '  <div class="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-700">',
            '    <h3 class="text-base font-semibold flex items-center gap-2">',
            '      <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/></svg>',
            '      Add to Investigation',
            '    </h3>',
            '    <button onclick="InvestigationModal.hide()" class="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 text-xl leading-none">&times;</button>',
            '  </div>',
            '  <div class="px-6 py-4">',
            '    <p class="text-sm text-slate-500 dark:text-slate-400 mb-3">Select an open investigation to link this evidence to:</p>',
            '    <div id="inv-modal-list" class="space-y-2 max-h-64 overflow-y-auto">',
            '      <p class="text-sm text-slate-400">Loading investigations…</p>',
            '    </div>',
            '  </div>',
            '  <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 dark:border-slate-700">',
            '    <button onclick="InvestigationModal.hide()" class="px-4 py-2 rounded-lg text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">Cancel</button>',
            '    <button id="inv-modal-confirm" onclick="InvestigationModal.confirm()" class="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition-colors">Add Evidence</button>',
            '  </div>',
            '</div>',
        ].join('');
        document.body.appendChild(el);
        // Close on backdrop click
        el.addEventListener('click', function (e) { if (e.target === el) hide(); });
    }

    async function _loadInvestigations() {
        var list = document.getElementById('inv-modal-list');
        if (!list) return;
        list.innerHTML = '<p class="text-sm text-slate-400">Loading…</p>';
        try {
            var data = await Auth.fetchJSON('/api/v1/investigations/list?status=open&limit=50');
            var items = Array.isArray(data) ? data : (data && data.investigations ? data.investigations : []);
            if (!items.length) {
                list.innerHTML = '<p class="text-sm text-slate-400">No open investigations found.</p>';
                return;
            }
            var esc = JDS.escapeHTML;
            list.innerHTML = items.map(function (inv, i) {
                return '<label class="flex items-center gap-3 p-3 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 cursor-pointer">'
                    + '<input type="radio" name="inv-modal-radio" value="' + esc(inv.id) + '" class="accent-blue-600"' + (i === 0 ? ' checked' : '') + '>'
                    + '<div class="flex-1 min-w-0">'
                    + '<p class="text-sm font-medium truncate">' + esc(inv.title || 'Investigation #' + inv.id) + '</p>'
                    + '<p class="text-xs text-slate-400">#' + esc(String(inv.id)) + ' · ' + esc(inv.priority || 'medium') + '</p>'
                    + '</div>'
                    + '</label>';
            }).join('');
        } catch (err) {
            list.innerHTML = '<p class="text-sm text-rose-500">Failed to load investigations.</p>';
        }
    }

    async function confirm() {
        var radio = document.querySelector('input[name="inv-modal-radio"]:checked');
        if (!radio) { alert('Please select an investigation.'); return; }
        var invId = radio.value;
        var btn = document.getElementById('inv-modal-confirm');
        btn.disabled = true;
        btn.textContent = 'Saving…';
        try {
            await Auth.fetchWithAuth('/api/v1/investigations/evidence', {
                method: 'POST',
                body: JSON.stringify({
                    investigation_id: invId,
                    evidence_type: _evidence.evidence_type || 'manual',
                    description: _evidence.description || '',
                    data: _evidence.data || {},
                    confidence: _evidence.confidence || 0.8
                })
            });
            if (typeof _evidence._onConfirm === 'function') {
                _evidence._onConfirm(invId);
            }
            hide();
            if (typeof JDS !== 'undefined' && JDS.toast) {
                JDS.toast('Evidence added to investigation #' + invId, 'success');
            }
        } catch (err) {
            alert('Failed to add evidence: ' + err);
        } finally {
            btn.disabled = false;
            btn.textContent = 'Add Evidence';
        }
    }

    return { show: show, hide: hide, confirm: confirm };
})();
