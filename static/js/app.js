/* ============================================
   App Initialization & Layout
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

    // Bottom nav items (mobile) — 4 main + "بیشتر"
    const bottomNavItems = [
        { path: '/', icon: '🏠', label: 'خانه' },
        { path: '/invoices/new', icon: '✏️', label: 'صدور فاکتور' },
        { path: '/invoices', icon: '📄', label: 'فاکتورها' },
        { path: '/customers', icon: '👥', label: 'مشتریان' },
        { path: '#more', icon: '☰', label: 'بیشتر' },
    ];

    const navHtml = navItems.map(n => {
        const active = (n.path === '/' && (hash === '/' || hash === ''))
            || (n.path !== '/' && hash.startsWith(n.path));
        return `<a href="#${n.path}" class="${active ? 'active' : ''}">
            <span class="icon">${n.icon}</span>${n.label}</a>`;
    }).join('');

    const bottomNavHtml = bottomNavItems.map(n => {
        const active = (n.path === '/' && (hash === '/' || hash === ''))
            || (n.path !== '/' && n.path !== '#more' && hash.startsWith(n.path));
        return `<a href="#${n.path}" class="${active ? 'active' : ''}" data-nav="${n.path}">
            <span class="nav-icon">${n.icon}</span>
            <span class="nav-label">${n.label}</span>
        </a>`;
    }).join('');

    return `
    <!-- Mobile Header (simplified) -->
    <div class="mobile-header">
        <button class="hamburger" onclick="toggleSidebar()">☰</button>
        <h3>Cat Invoice</h3>
        <span></span>
    </div>
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>

    <!-- Sidebar (Desktop + Mobile slide) -->
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

    <!-- Bottom Navigation (Mobile) -->
    <nav class="bottom-nav" id="bottomNav">${bottomNavHtml}</nav>

    <!-- More Menu Overlay (Mobile) -->
    <div class="more-overlay" id="moreOverlay" onclick="closeMoreMenu()">
        <div class="more-menu" onclick="event.stopPropagation()">
            <div class="more-menu-header">
                <h3>بیشتر</h3>
                <button class="modal-close" onclick="closeMoreMenu()">&times;</button>
            </div>
            <a href="#/products" onclick="closeMoreMenu()">📦 محصولات</a>
            <a href="#/banks" onclick="closeMoreMenu()">🏦 حساب‌های بانکی</a>
            <a href="#/reports" onclick="closeMoreMenu()">📊 گزارش‌ها</a>
            <a href="#/settings" onclick="closeMoreMenu()">⚙️ تنظیمات</a>
            <div class="more-divider"></div>
            <a href="javascript:API.logout()" class="more-logout">🚪 خروج</a>
        </div>
    </div>

    <!-- FAB (Mobile) -->
    <button class="fab" onclick="Router.navigate('/invoices/new')" title="فاکتور جدید">+</button>

    <!-- Main Content -->
    <div class="main-content">${content}</div>`;
}

function toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('open');
    document.getElementById('sidebarOverlay')?.classList.toggle('show');
}

function closeMoreMenu() {
    document.getElementById('moreOverlay')?.classList.remove('show');
}

// Show more menu when "بیشتر" is clicked
document.addEventListener('click', (e) => {
    const nav = e.target.closest('[data-nav="#more"]');
    if (nav) {
        e.preventDefault();
        document.getElementById('moreOverlay')?.classList.add('show');
    }
});

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
