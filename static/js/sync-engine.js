/* ============================================================
   Cat Invoice — Sync Engine
   Processes offline queue when online.
   Handles: retry, idempotency, conflict detection.
   ============================================================ */

const CatSync = (() => {
    const MAX_RETRIES = 5;
    const RETRY_DELAY_MS = 2000; // base delay, doubles each retry
    let isSyncing = false;
    let statusListeners = [];

    // ---- Status management ----
    function onStatusChange(fn) {
        statusListeners.push(fn);
    }

    function emitStatus(status) {
        statusListeners.forEach(fn => fn(status));
    }

    // ---- Check online ----
    function isOnline() {
        return navigator.onLine;
    }

    // ---- Main sync loop ----
    async function syncAll() {
        if (isSyncing || !isOnline()) return;
        isSyncing = true;
        emitStatus({ state: 'syncing', message: 'در حال همگام‌سازی...' });

        try {
            const queue = await CatDB.getPendingQueue();
            if (queue.length === 0) {
                emitStatus({ state: 'idle', message: 'همگام‌سازی انجام شد ✓' });
                isSyncing = false;
                return;
            }

            let successCount = 0;
            let failCount = 0;

            for (const item of queue) {
                if (!isOnline()) break; // Stop if went offline mid-sync

                try {
                    item.status = 'syncing';
                    await CatDB.updateQueueItem(item);

                    const result = await processQueueItem(item);

                    if (result.success) {
                        await CatDB.deleteQueueItem(item.id);
                        successCount++;
                        // If this was a draft, mark it synced
                        if (item.clientId) {
                            const draft = await CatDB.getDraft(item.clientId);
                            if (draft) {
                                draft.status = 'synced';
                                draft.serverId = result.serverId;
                                await CatDB.saveDraft(draft);
                            }
                        }
                    } else if (result.conflict) {
                        // Conflict: mark and keep in queue
                        item.status = 'conflict';
                        item.conflictData = result.conflictData;
                        await CatDB.updateQueueItem(item);
                        failCount++;
                    } else {
                        throw new Error(result.error || 'Sync failed');
                    }
                } catch (err) {
                    item.retryCount = (item.retryCount || 0) + 1;
                    if (item.retryCount >= MAX_RETRIES) {
                        item.status = 'failed';
                        item.lastError = err.message;
                    } else {
                        item.status = 'pending';
                        // Exponential backoff
                        item.nextRetryAt = Date.now() + RETRY_DELAY_MS * Math.pow(2, item.retryCount - 1);
                    }
                    await CatDB.updateQueueItem(item);
                    failCount++;
                }
            }

            const stats = await CatDB.getQueueStats();
            if (failCount === 0) {
                emitStatus({ state: 'done', message: `${successCount} عملیات همگام‌سازی شد ✓`, stats });
            } else {
                emitStatus({
                    state: 'partial',
                    message: `${successCount} موفق، ${failCount} ناموفق`,
                    stats
                });
            }
        } catch (err) {
            emitStatus({ state: 'error', message: 'خطا در همگام‌سازی: ' + err.message });
        } finally {
            isSyncing = false;
        }
    }

    // ---- Process a single queue item ----
    async function processQueueItem(item) {
        const headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Idempotency-Key': item.clientId, // Prevent duplicates
        };

        try {
            const resp = await fetch(item.url, {
                method: item.method || 'POST',
                headers,
                body: JSON.stringify(item.payload),
                credentials: 'same-origin',
            });

            if (resp.status === 409) {
                // Conflict detected by server
                const data = await resp.json();
                return { success: false, conflict: true, conflictData: data };
            }

            if (resp.ok) {
                const data = await resp.json();
                return { success: true, serverId: data.id || data.invoice_id };
            }

            const errData = await resp.json().catch(() => ({}));
            return { success: false, error: errData.detail || errData.error || `HTTP ${resp.status}` };
        } catch (err) {
            return { success: false, error: err.message };
        }
    }

    // ---- Enqueue an operation ----
    async function enqueueOperation(type, url, method, payload, clientId) {
        const item = {
            type,
            url,
            method: method || 'POST',
            payload,
            clientId: clientId || crypto.randomUUID(),
        };
        await CatDB.enqueue(item);

        // Try immediate sync if online
        if (isOnline()) {
            setTimeout(() => syncAll(), 500);
        } else {
            // Register for background sync if available
            if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
                try {
                    const reg = await navigator.serviceWorker.ready;
                    if (reg.sync) await reg.sync.register('cat-invoice-sync');
                } catch { /* Background sync not supported */ }
            }
        }

        return item.clientId;
    }

    // ---- Force sync (user-triggered) ----
    async function forceSync() {
        // Retry failed items too
        const queue = await CatDB.getQueue();
        for (const item of queue) {
            if (item.status === 'failed') {
                item.status = 'pending';
                item.retryCount = 0;
                await CatDB.updateQueueItem(item);
            }
        }
        await syncAll();
    }

    // ---- Resolve conflict ----
    async function resolveConflict(queueItemId, resolution) {
        // resolution: 'server' (keep server) | 'client' (force push)
        const queue = await CatDB.getQueue();
        const item = queue.find(i => i.id === queueItemId);
        if (!item) return;

        if (resolution === 'server') {
            await CatDB.deleteQueueItem(item.id);
            if (item.clientId) {
                const draft = await CatDB.getDraft(item.clientId);
                if (draft) {
                    draft.status = 'conflict_resolved';
                    await CatDB.saveDraft(draft);
                }
            }
        } else if (resolution === 'client') {
            item.status = 'pending';
            item.retryCount = 0;
            item.forceOverwrite = true;
            item.payload._conflict_resolution = 'client_wins';
            await CatDB.updateQueueItem(item);
            if (isOnline()) await syncAll();
        }
    }

    // ---- Get sync status summary ----
    async function getStatus() {
        const stats = await CatDB.getQueueStats();
        const lastSync = await CatDB.getMeta('lastSyncAt');
        return {
            isOnline: isOnline(),
            isSyncing,
            stats,
            lastSyncAt: lastSync,
        };
    }

    // ---- Cache reference data for offline use ----
    async function cacheRefData() {
        if (!isOnline()) return;
        try {
            // Cache customers
            const custResp = await fetch('/search/customers/?q=', { credentials: 'same-origin' });
            if (custResp.ok) {
                const custData = await custResp.json();
                await CatDB.saveRefData('customers', custData);
            }

            // Cache products
            const prodResp = await fetch('/search/products/?q=', { credentials: 'same-origin' });
            if (prodResp.ok) {
                const prodData = await prodResp.json();
                await CatDB.saveRefData('products', prodData);
            }

            // Cache units
            const unitResp = await fetch('/units/', { credentials: 'same-origin' });
            if (unitResp.ok) {
                const unitData = await unitResp.json();
                await CatDB.saveRefData('units', unitData);
            }

            await CatDB.setMeta('lastRefDataSync', Date.now());
        } catch { /* ignore — will retry later */ }
    }

    // ---- Helpers ----
    function getCsrfToken() {
        const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
        return cookie ? cookie.split('=')[1] : '';
    }

    // ---- Auto-sync on reconnect ----
    function init() {
        window.addEventListener('online', () => {
            emitStatus({ state: 'online', message: 'آنلاین 🟢' });
            setTimeout(() => syncAll(), 1000);
            cacheRefData();
        });

        window.addEventListener('offline', () => {
            emitStatus({ state: 'offline', message: 'آفلاین 🔴' });
        });

        // Listen for SW sync messages
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.addEventListener('message', (event) => {
                if (event.data?.type === 'SYNC_REQUESTED') {
                    syncAll();
                }
            });
        }

        // Periodic sync attempt (every 5 min if online)
        setInterval(() => {
            if (isOnline()) {
                const pending = CatDB.getPendingQueue();
                pending.then(q => { if (q.length > 0) syncAll(); });
            }
        }, 5 * 60 * 1000);

        // Initial status
        if (!isOnline()) {
            emitStatus({ state: 'offline', message: 'آفلاین 🔴' });
        }
    }

    return {
        init,
        syncAll,
        forceSync,
        enqueueOperation,
        resolveConflict,
        getStatus,
        cacheRefData,
        isOnline,
        onStatusChange,
    };
})();
