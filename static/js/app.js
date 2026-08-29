/* ============================================
   App Initialization & Sidebar
   ============================================ */

function buildLayout(content) {
    const user = API.getUser();
    const name = user ? (user.first_name + ' ' + user.last_name).trim() || user.username : '';
    const hash = window.location.hash.slice(1) || '/';

    const navItems = [
        { path: '/', icon: '🏠', label: 'داشبورد' },
        { path: '/invoices', icon: '📄', label: 'فاکتورها' },
        { path: '/customers', icon: '👥', label: 'مشتریان' },
        { path: '/products', icon: '📦', label: 'محصولات' },
        { path: '/banks', icon: '🏦', label: 'حساب‌های بانکی' },
        { path: '/reports', icon: '📊', label: 'گزارش‌ها' },
        { path: '/settings', icon: '⚙️', label: 'تنظیمات' },
    ];

    const navHtml = navItems.map(n => {
        const active = (n.path === '/' && (hash === '/' || hash === ''))
            || (n.path !== '/' && hash.startsWith(n.path));
        return `<a href="#${n.path}" class="${active ? 'active' : ''}">
            <span class="icon">${n.icon}</span>${n.label}</a>`;
    }).join('');

    return `
    <!-- Mobile Header -->
    <div class="mobile-header">
        <button class="hamburger" onclick="toggleSidebar()">☰</button>
        <h3>Cat Invoice</h3>
        <button class="btn btn-sm" onclick="API.logout()" style="background:rgba(255,255,255,0.15);color:#fff;">خروج</button>
    </div>
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>

    <!-- Sidebar -->
    <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h2>🐱 Cat Invoice</h2>
            <div class="user-name">${escHtml(name)}</div>
        </div>
        <div class="sidebar-nav">${navHtml}</div>
        <div class="sidebar-footer">
            <a href="#/settings" style="color:rgba(255,255,255,0.7);text-decoration:none;font-size:13px;">⚙️ تنظیمات</a>
            <button class="btn btn-sm" onclick="API.logout()"
                style="margin-top:8px;width:100%;justify-content:center;background:rgba(255,255,255,0.1);color:#fff;">
                خروج
            </button>
        </div>
    </div>

    <!-- Main -->
    <div class="main-content">${content}</div>`;
}

function toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('open');
    document.getElementById('sidebarOverlay')?.classList.toggle('show');
}

/* Route Registration */
Router.register('/', () => renderDashboard());
Router.register('/login', () => renderLogin());
Router.register('/register', () => renderRegister());
Router.register('/invoices', () => renderInvoices());
Router.register('/invoices/new', (p) => renderInvoiceForm({ id: 'new' }));
Router.register('/invoices/:id', (p) => renderInvoiceForm(p));
Router.register('/customers', () => renderCustomers());
Router.register('/products', () => renderProducts());
Router.register('/banks', () => renderBanks());
Router.register('/reports', () => renderReports());
Router.register('/settings', () => renderSettings());

/* Init */
Router.init();
