/* ============================================================
   Cat Invoice — PWA Manager
   Handles: SW registration, install prompt, status UI,
   push notifications, logout cleanup.
   ============================================================ */

const CatPWA = (() => {
    let deferredPrompt = null;
    const INSTALL_DISMISSED_KEY = 'pwa-install-dismissed-v2';

    // ---- Register Service Worker ----
    async function registerSW() {
        if (!('serviceWorker' in navigator)) return;

        try {
            const reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' });
            console.log('[PWA] SW registered:', reg.scope);

            // Check for updates every 60 min
            setInterval(() => reg.update(), 60 * 60 * 1000);

            reg.addEventListener('updatefound', () => {
                const newWorker = reg.installing;
                newWorker.addEventListener('statechange', () => {
                    if (newWorker.state === 'activated') {
                        showUpdateNotification();
                    }
                });
            });
        } catch (err) {
            console.warn('[PWA] SW registration failed:', err);
        }
    }

    // ---- Is running as installed PWA? ----
    function isStandalone() {
        return window.matchMedia('(display-mode: standalone)').matches ||
               window.navigator.standalone === true; // iOS Safari
    }

    // ---- Install prompt ----
    function initInstallPrompt() {
        // Don't show anything if already running as installed PWA
        if (isStandalone()) return;

        // Always show header icon (user might have dismissed banner)
        showHeaderInstallIcon();

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;

            // Show banner only if NEVER dismissed before
            if (!localStorage.getItem(INSTALL_DISMISSED_KEY)) {
                showInstallBanner();
            }
        });

        window.addEventListener('appinstalled', () => {
            deferredPrompt = null;
            hideInstallBanner();
            hideHeaderInstallIcon();
            localStorage.removeItem(INSTALL_DISMISSED_KEY);
            console.log('[PWA] App installed');
        });
    }

    async function promptInstall() {
        if (!deferredPrompt) {
            // No prompt available — show instructions
            alert('برای نصب Cat Invoice:\n\n۱. منوی مرورگر (⋮) را باز کنید\n۲. «افزودن به صفحه اصلی» را بزنید');
            return false;
        }
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        deferredPrompt = null;
        hideInstallBanner();
        if (outcome === 'accepted') {
            hideHeaderInstallIcon();
            localStorage.removeItem(INSTALL_DISMISSED_KEY);
        }
        return outcome === 'accepted';
    }

    // ---- Install banner (bottom toast) ----
    function showInstallBanner() {
        if (document.getElementById('pwaInstallBanner')) return;
        const banner = document.createElement('div');
        banner.id = 'pwaInstallBanner';
        banner.className = 'pwa-install-banner';
        banner.innerHTML = `
            <span>📱 Cat Invoice را روی دستگاه خود نصب کنید</span>
            <button onclick="CatPWA.promptInstall()" class="btn btn-sm btn-primary">نصب</button>
            <button onclick="CatPWA.dismissInstall()" class="btn btn-sm" style="background:transparent;color:var(--text-secondary);">✕</button>
        `;
        document.body.appendChild(banner);
        setTimeout(() => banner.classList.add('show'), 100);
    }

    function hideInstallBanner() {
        const b = document.getElementById('pwaInstallBanner');
        if (b) b.remove();
    }

    function dismissInstall() {
        hideInstallBanner();
        localStorage.setItem(INSTALL_DISMISSED_KEY, '1');
        // Header icon stays — user can still install later
    }

    // ---- Header install icon (persistent in sidebar) ----
    function showHeaderInstallIcon() {
        if (document.getElementById('pwaSidebarInstallBtn')) return;

        // Sidebar header — small emoji, always visible
        const sidebarHeader = document.querySelector('.sidebar-header');
        if (sidebarHeader) {
            const btn = document.createElement('button');
            btn.id = 'pwaSidebarInstallBtn';
            btn.className = 'pwa-sidebar-install-btn';
            btn.title = 'نصب برنامه';
            btn.textContent = '📲';
            btn.onclick = () => promptInstall();
            // Insert after h2
            const h2 = sidebarHeader.querySelector('h2');
            if (h2) h2.insertAdjacentElement('afterend', btn);
            else sidebarHeader.appendChild(btn);
        }
    }

    function hideHeaderInstallIcon() {
        document.getElementById('pwaSidebarInstallBtn')?.remove();
    }

    // ---- Update notification ----
    function showUpdateNotification() {
        const toast = document.createElement('div');
        toast.className = 'toast success';
        toast.innerHTML = 'نسخه جدید برنامه موجود است. <button onclick="location.reload()" class="btn btn-sm btn-primary" style="margin-right:8px;">بروزرسانی</button>';
        const container = document.getElementById('toasts') || createToastContainer();
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 15000);
    }

    function createToastContainer() {
        const c = document.createElement('div');
        c.id = 'toasts';
        c.className = 'toast-container';
        document.querySelector('.main-content')?.prepend(c);
        return c;
    }

    // ---- Status bar UI ----
    function initStatusBar() {
        const statusEl = document.getElementById('pwaStatus');
        const iconEl = document.getElementById('pwaStatusIcon');
        const textEl = document.getElementById('pwaStatusText');
        const countEl = document.getElementById('pwaQueueCount');
        const syncBtn = document.getElementById('pwaSyncBtn');

        if (!statusEl) return;

        CatSync.onStatusChange(async (status) => {
            // Show status bar when offline or syncing
            if (status.state === 'offline' || status.state === 'syncing' || status.state === 'partial') {
                statusEl.style.display = 'flex';
                statusEl.className = 'pwa-status pwa-status-' + status.state;
            } else if (status.state === 'online' || status.state === 'done') {
                // Show briefly then hide
                statusEl.style.display = 'flex';
                statusEl.className = 'pwa-status pwa-status-' + status.state;
                setTimeout(() => { statusEl.style.display = 'none'; }, 3000);
            }

            // Update icon
            const icons = { online: '🟢', offline: '🔴', syncing: '🔄', done: '✓', partial: '⚠', error: '⚠', idle: '✓' };
            iconEl.textContent = icons[status.state] || '🔴';

            // Update text
            textEl.textContent = status.message || '';

            // Queue count
            const stats = status.stats || await CatDB.getQueueStats().catch(() => ({ pending: 0 }));
            if (stats.pending > 0) {
                countEl.style.display = 'inline';
                countEl.textContent = `(${stats.pending} در صف)`;
                syncBtn.style.display = 'inline-flex';
            } else {
                countEl.style.display = 'none';
                syncBtn.style.display = 'none';
            }
        });

        // Initial state
        if (!navigator.onLine) {
            statusEl.style.display = 'flex';
            statusEl.className = 'pwa-status pwa-status-offline';
            iconEl.textContent = '🔴';
            textEl.textContent = 'آفلاین';
        }
    }

    // ---- Push Notifications ----
    async function initPushNotifications() {
        if (!('Notification' in window) || !('serviceWorker' in navigator)) return;

        // Only ask if not already decided
        if (Notification.permission === 'default') {
            // Don't auto-ask — wait for user action
            return;
        }

        if (Notification.permission === 'granted') {
            await subscribePush();
        }
    }

    async function requestPushPermission() {
        if (!('Notification' in window)) {
            console.warn('[PWA] Notifications not supported');
            return false;
        }

        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            await subscribePush();
            return true;
        }
        return false;
    }

    async function subscribePush() {
        try {
            const reg = await navigator.serviceWorker.ready;
            const existing = await reg.pushManager.getSubscription();
            if (existing) return existing;

            // Subscribe with a placeholder VAPID key
            // In production, replace with real VAPID public key from server
            const vapidKey = 'BEl62iUYgUivxIkv69yViE89asdfghjkl0987654321qwertyuiop';
            const subscription = await reg.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: urlBase64ToUint8Array(vapidKey),
            });

            // Send subscription to server
            await fetch('/api/push/subscribe/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(subscription.toJSON()),
                credentials: 'same-origin',
            });

            console.log('[PWA] Push subscribed');
            return subscription;
        } catch (err) {
            console.warn('[PWA] Push subscription failed:', err);
        }
    }

    // ---- Logout cleanup ----
    function initLogoutCleanup() {
        // Intercept logout forms to clear offline data
        document.querySelectorAll('#logoutForm, form[action*="logout"]').forEach(form => {
            form.addEventListener('submit', async () => {
                try {
                    // Clear all caches
                    const cacheNames = await caches.keys();
                    await Promise.all(cacheNames.filter(n => n.startsWith('cat-invoice-')).map(n => caches.delete(n)));

                    // Clear IndexedDB
                    await CatDB.clearAll();

                    // Unsubscribe push
                    const reg = await navigator.serviceWorker.ready;
                    const sub = await reg.pushManager.getSubscription();
                    if (sub) await sub.unsubscribe();

                    // Clear install dismissed flag
                    localStorage.removeItem(INSTALL_DISMISSED_KEY);

                    console.log('[PWA] Logout cleanup done');
                } catch (err) {
                    console.warn('[PWA] Logout cleanup error:', err);
                }
            });
        });
    }

    // ---- Helpers ----
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
        const rawData = atob(base64);
        return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
    }

    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    // ---- Init everything ----
    async function init() {
        await CatDB.open();
        CatSync.init();
        await registerSW();
        initInstallPrompt();
        initStatusBar();
        initLogoutCleanup();
        await initPushNotifications();

        // Cache reference data on first load
        if (navigator.onLine) {
            CatSync.cacheRefData();
        }
    }

    return {
        init,
        registerSW,
        promptInstall,
        dismissInstall,
        requestPushPermission,
        subscribePush,
    };
})();

// Auto-init when DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => CatPWA.init());
} else {
    CatPWA.init();
}
