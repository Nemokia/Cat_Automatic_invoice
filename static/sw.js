/* ============================================================
   Cat Invoice — Service Worker
   Cache strategies:
   - Static assets: Cache-First (long-lived, versioned)
   - Pages: Network-First with offline fallback
   - API GET: Stale-While-Revalidate
   - API POST/PUT/DELETE: pass-through (handled by sync-engine.js)
   ============================================================ */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `cat-invoice-static-${CACHE_VERSION}`;
const PAGE_CACHE = `cat-invoice-pages-${CACHE_VERSION}`;
const API_CACHE = `cat-invoice-api-${CACHE_VERSION}`;

// Static assets to pre-cache on install
const PRECACHE_URLS = [
    '/',
    '/static/css/style.css',
    '/static/js/utils.js',
    '/static/js/jalali.js',
    '/static/js/date-scroller.js',
    '/static/js/unit-select.js',
    '/static/js/layout.js',
    '/static/js/offline-db.js',
    '/static/js/sync-engine.js',
    '/static/js/pwa-manager.js',
    '/static/manifest.json',
    '/static/icons/favicon.svg',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
];

// Pages to cache for offline access
const OFFLINE_PAGES = [
    '/',
    '/invoices/',
    '/invoices/new/',
    '/customers/',
    '/products/',
    '/banks/',
    '/reports/',
];

// ---- Install ----
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(PRECACHE_URLS);
        }).then(() => {
            // Also cache offline pages
            return caches.open(PAGE_CACHE).then((cache) => {
                return Promise.allSettled(
                    OFFLINE_PAGES.map((url) =>
                        fetch(url, { credentials: 'same-origin' })
                            .then((resp) => {
                                if (resp.ok) return cache.put(url, resp);
                            })
                            .catch(() => {/* ignore — will try on first visit */})
                    )
                );
            });
        }).then(() => self.skipWaiting())
    );
});

// ---- Activate: clean old caches ----
self.addEventListener('activate', (event) => {
    const keepCaches = [STATIC_CACHE, PAGE_CACHE, API_CACHE];
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((k) => k.startsWith('cat-invoice-') && !keepCaches.includes(k))
                    .map((k) => caches.delete(k))
            );
        }).then(() => self.clients.claim())
    );
});

// ---- Fetch handler ----
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Skip non-GET for caching (POST/PUT/DELETE go to network directly)
    if (request.method !== 'GET') return;

    // Skip cross-origin requests (CDN Chart.js etc. — let them pass)
    if (url.origin !== location.origin) {
        // Cache CDN resources (Chart.js) with Cache-First
        if (url.hostname.includes('cdn.jsdelivr.net') || url.hostname.includes('fonts.googleapis.com')) {
            event.respondWith(
                caches.open(STATIC_CACHE).then((cache) =>
                    cache.match(request).then((cached) => {
                        if (cached) return cached;
                        return fetch(request).then((resp) => {
                            if (resp.ok) cache.put(request, resp.clone());
                            return resp;
                        });
                    })
                )
            );
        }
        return;
    }

    // API requests: Stale-While-Revalidate
    if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/units/') ||
        url.pathname.startsWith('/search/')) {
        event.respondWith(staleWhileRevalidate(request, API_CACHE));
        return;
    }

    // Static assets: Cache-First
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(request, STATIC_CACHE));
        return;
    }

    // Pages: Network-First with offline fallback
    event.respondWith(networkFirstWithFallback(request));
});

// ---- Cache strategies ----

async function cacheFirst(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    if (cached) return cached;
    try {
        const resp = await fetch(request);
        if (resp.ok) cache.put(request, resp.clone());
        return resp;
    } catch {
        return new Response('Offline', { status: 503, statusText: 'Offline' });
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cache = await caches.open(cacheName);
    const cached = await cache.match(request);
    const fetchPromise = fetch(request).then((resp) => {
        if (resp.ok) cache.put(request, resp.clone());
        return resp;
    }).catch(() => cached);

    return cached || fetchPromise;
}

async function networkFirstWithFallback(request) {
    const cache = await caches.open(PAGE_CACHE);
    try {
        const resp = await fetch(request);
        if (resp.ok) cache.put(request, resp.clone());
        return resp;
    } catch {
        // Try cache
        const cached = await cache.match(request);
        if (cached) return cached;
        // Try the root page as ultimate fallback
        const root = await cache.match('/');
        if (root) return root;
        return new Response(OFFLINE_HTML, {
            headers: { 'Content-Type': 'text/html; charset=utf-8' },
        });
    }
}

// ---- Offline fallback HTML ----
const OFFLINE_HTML = `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>آفلاین — Cat Invoice</title>
    <style>
        body { background: #092328; color: #e8f0ec; font-family: Vazirmatn, sans-serif;
               display: flex; align-items: center; justify-content: center;
               min-height: 100vh; margin: 0; direction: rtl; text-align: center; }
        .box { max-width: 400px; padding: 40px; }
        h1 { font-size: 48px; margin-bottom: 16px; }
        p { color: #9ab5a5; line-height: 1.8; }
        .btn { display: inline-block; margin-top: 24px; padding: 12px 32px;
               background: #2A835F; color: #fff; border: none; border-radius: 8px;
               font-size: 16px; cursor: pointer; text-decoration: none; }
    </style>
</head>
<body>
    <div class="box">
        <h1>📡</h1>
        <h2>شما آفلاین هستید</h2>
        <p>اتصال اینترنت برقرار نیست. لطفاً اتصال خود را بررسی کنید و دوباره تلاش کنید.</p>
        <button class="btn" onclick="location.reload()">تلاش مجدد</button>
    </div>
</body>
</html>`;

// ---- Push Notifications ----
self.addEventListener('push', (event) => {
    let data = { title: 'Cat Invoice', body: 'اعلان جدید' };
    try {
        data = event.data.json();
    } catch {
        data.body = event.data?.text() || data.body;
    }

    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: '/static/icons/icon-192.png',
            badge: '/static/icons/icon-192.png',
            dir: 'rtl',
            lang: 'fa',
            tag: data.tag || 'cat-invoice-notification',
            data: data.url || '/',
            actions: data.actions || [],
        })
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const url = event.notification.data || '/';
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((wins) => {
            // Focus existing window if open
            for (const w of wins) {
                if (w.url.includes(url) && 'focus' in w) return w.focus();
            }
            return clients.openWindow(url);
        })
    );
});

// ---- Background Sync ----
self.addEventListener('sync', (event) => {
    if (event.tag === 'cat-invoice-sync') {
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Notify all clients to trigger sync
    const clientsList = await self.clients.matchAll();
    for (const client of clientsList) {
        client.postMessage({ type: 'SYNC_REQUESTED' });
    }
}
