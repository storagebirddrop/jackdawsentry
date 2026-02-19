/**
 * Jackdaw Sentry — Shared Navigation Component
 * Injects sidebar + topbar into every page. Handles dark mode toggle.
 */

const Nav = (function () {
    const DARK_KEY = 'jds_dark_mode';

    const pages = [
        { href: '/',               icon: 'layout-dashboard', label: 'Dashboard' },
        { href: '/analysis',       icon: 'search',           label: 'Analysis' },
        { href: '/graph',          icon: 'git-branch',       label: 'Graph Explorer' },
        { href: '/compliance',     icon: 'shield-check',     label: 'Compliance' },
        { href: '/compliance/analytics', icon: 'bar-chart-3', label: 'Analytics' },
        { href: '/intelligence',   icon: 'radar',            label: 'Intelligence' },
        { href: '/investigations', icon: 'briefcase',        label: 'Investigations' },
        { href: '/reports',        icon: 'file-text',        label: 'Reports' },
    ];

    /** Determine which page is active based on current path */
    function activePath() {
        const p = window.location.pathname.replace(/\/+$/, '') || '/';
        return p;
    }

    /** Apply or remove dark class on <html> */
    function applyDark(dark) {
        document.documentElement.classList.toggle('dark', dark);
        localStorage.setItem(DARK_KEY, dark ? '1' : '0');
    }

    /** Read stored preference; default to system preference */
    function isDark() {
        const stored = localStorage.getItem(DARK_KEY);
        if (stored !== null) return stored === '1';
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }

    /** Build the sidebar HTML string */
    function sidebarHTML() {
        const current = activePath();
        const user = (typeof Auth !== 'undefined') ? Auth.getUser() : null;
        const initials = user ? (user.username || 'U').substring(0, 2).toUpperCase() : 'JS';
        const username = user ? user.username : 'User';
        const role = user ? (user.role || 'analyst') : 'analyst';

        let navItems = '';
        pages.forEach(function (p) {
            const active = (current === p.href);
            const cls = active
                ? 'bg-blue-600 text-white'
                : 'text-slate-300 hover:bg-slate-700 hover:text-white';
            navItems += '<a href="' + p.href + '" class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ' + cls + '">'
                + '<i data-lucide="' + p.icon + '" class="w-5 h-5 flex-shrink-0"></i>'
                + '<span class="sidebar-label">' + p.label + '</span></a>';
        });

        return ''
            + '<aside id="jds-sidebar" class="fixed inset-y-0 left-0 z-40 w-64 bg-slate-900 dark:bg-slate-950 border-r border-slate-800 flex flex-col transition-transform duration-200 -translate-x-full lg:translate-x-0">'
            + '  <div class="flex items-center gap-3 px-4 h-16 border-b border-slate-800">'
            + '    <svg class="h-8 w-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
            + '    <span class="sidebar-label text-lg font-bold text-white tracking-tight">Jackdaw Sentry</span>'
            + '  </div>'
            + '  <nav class="flex-1 overflow-y-auto px-3 py-4 space-y-1">' + navItems + '</nav>'
            + '  <div class="px-3 py-4 border-t border-slate-800">'
            + '    <div class="flex items-center gap-3 px-3 py-2">'
            + '      <div class="h-9 w-9 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-semibold">' + initials + '</div>'
            + '      <div class="sidebar-label">'
            + '        <p class="text-sm font-medium text-white">' + username + '</p>'
            + '        <p class="text-xs text-slate-400 capitalize">' + role + '</p>'
            + '      </div>'
            + '    </div>'
            + '    <button onclick="Auth.logout()" class="mt-2 w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-700 hover:text-white transition-colors">'
            + '      <i data-lucide="log-out" class="w-4 h-4"></i><span class="sidebar-label">Sign out</span>'
            + '    </button>'
            + '  </div>'
            + '</aside>';
    }

    /** Build the topbar HTML string */
    function topbarHTML() {
        const current = activePath();
        const page = pages.find(function (p) { return p.href === current; }) || pages[0];

        return ''
            + '<header id="jds-topbar" class="sticky top-0 z-30 lg:ml-64 h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 sm:px-6">'
            + '  <div class="flex items-center gap-3">'
            + '    <button id="jds-menu-toggle" class="lg:hidden p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800">'
            + '      <i data-lucide="menu" class="w-5 h-5"></i>'
            + '    </button>'
            + '    <h1 class="text-lg font-semibold text-slate-900 dark:text-white">' + page.label + '</h1>'
            + '  </div>'
            + '  <div class="flex items-center gap-3">'
            + '    <div class="hidden sm:flex items-center gap-2 text-sm">'
            + '      <span class="inline-block w-2 h-2 rounded-full bg-emerald-500"></span>'
            + '      <span class="text-slate-500 dark:text-slate-400">Systems Online</span>'
            + '    </div>'
            + '    <button id="jds-dark-toggle" class="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 dark:text-slate-400" title="Toggle dark mode">'
            + '      <i data-lucide="' + (isDark() ? 'sun' : 'moon') + '" class="w-5 h-5"></i>'
            + '    </button>'
            + '  </div>'
            + '</header>';
    }

    /** Backdrop for mobile sidebar */
    function backdropHTML() {
        return '<div id="jds-backdrop" class="fixed inset-0 z-30 bg-black/50 hidden lg:hidden"></div>';
    }

    /** Inject nav into page and wire events */
    function init() {
        // Apply dark mode immediately (before paint)
        applyDark(isDark());

        // Inject HTML at start of body
        const wrapper = document.createElement('div');
        wrapper.innerHTML = sidebarHTML() + backdropHTML() + topbarHTML();
        while (wrapper.firstChild) {
            document.body.insertBefore(wrapper.firstChild, document.body.firstChild);
        }

        // Main content wrapper needs left margin on desktop
        const main = document.getElementById('jds-main');
        if (main) {
            main.classList.add('lg:ml-64');
        }

        // Re-init Lucide icons for injected elements
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Mobile menu toggle
        var sidebar = document.getElementById('jds-sidebar');
        var backdrop = document.getElementById('jds-backdrop');
        var menuBtn = document.getElementById('jds-menu-toggle');

        function openSidebar() {
            sidebar.classList.remove('-translate-x-full');
            backdrop.classList.remove('hidden');
        }
        function closeSidebar() {
            sidebar.classList.add('-translate-x-full');
            backdrop.classList.add('hidden');
        }

        if (menuBtn) menuBtn.addEventListener('click', openSidebar);
        if (backdrop) backdrop.addEventListener('click', closeSidebar);

        // Dark mode toggle
        var darkBtn = document.getElementById('jds-dark-toggle');
        if (darkBtn) {
            darkBtn.addEventListener('click', function () {
                var nowDark = !isDark();
                applyDark(nowDark);
                // Swap icon
                var icon = darkBtn.querySelector('[data-lucide]');
                if (icon) {
                    icon.setAttribute('data-lucide', nowDark ? 'sun' : 'moon');
                    if (typeof lucide !== 'undefined') lucide.createIcons();
                }
            });
        }
    }

    return { init, isDark, applyDark };
})();

// Auto-init when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    Nav.init();
});
