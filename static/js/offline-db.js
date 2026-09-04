/* ============================================================
   Cat Invoice — IndexedDB Offline Storage
   Stores: draft invoices, offline queue, reference data
   ============================================================ */

const CatDB = (() => {
    const DB_NAME = 'cat-invoice-db';
    const DB_VERSION = 1;
    let db = null;

    // ---- Open/Init ----
    function open() {
        return new Promise((resolve, reject) => {
            if (db) return resolve(db);
            const req = indexedDB.open(DB_NAME, DB_VERSION);

            req.onupgradeneeded = (e) => {
                const d = e.target.result;

                // Draft invoices (offline-created)
                if (!d.objectStoreNames.contains('drafts')) {
                    const store = d.createObjectStore('drafts', { keyPath: 'clientId' });
                    store.createIndex('updatedAt', 'updatedAt');
                    store.createIndex('status', 'status'); // 'draft' | 'pending' | 'synced'
                }

                // Offline operation queue
                if (!d.objectStoreNames.contains('queue')) {
                    const store = d.createObjectStore('queue', { keyPath: 'id', autoIncrement: true });
                    store.createIndex('createdAt', 'createdAt');
                    store.createIndex('status', 'status'); // 'pending' | 'syncing' | 'failed'
                    store.createIndex('type', 'type'); // 'create_invoice' | 'update_invoice' | ...
                }

                // Reference data cache (customers, products, banks for autocomplete)
                if (!d.objectStoreNames.contains('refdata')) {
                    const store = d.createObjectStore('refdata', { keyPath: 'type' });
                }

                // Sync metadata
                if (!d.objectStoreNames.contains('meta')) {
                    d.createObjectStore('meta', { keyPath: 'key' });
                }
            };

            req.onsuccess = (e) => {
                db = e.target.result;
                resolve(db);
            };

            req.onerror = (e) => reject(e.target.error);
        });
    }

    // ---- Generic helpers ----
    function tx(storeName, mode) {
        return db.transaction(storeName, mode).objectStore(storeName);
    }

    function promisify(req) {
        return new Promise((resolve, reject) => {
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    // ---- Drafts ----
    async function saveDraft(draft) {
        await open();
        draft.updatedAt = Date.now();
        draft.status = draft.status || 'draft';
        return promisify(tx('drafts', 'readwrite').put(draft));
    }

    async function getDraft(clientId) {
        await open();
        return promisify(tx('drafts', 'readonly').get(clientId));
    }

    async function getAllDrafts() {
        await open();
        return promisify(tx('drafts', 'readonly').getAll());
    }

    async function deleteDraft(clientId) {
        await open();
        return promisify(tx('drafts', 'readwrite').delete(clientId));
    }

    async function getPendingDrafts() {
        await open();
        const idx = tx('drafts', 'readonly').index('status');
        return promisify(idx.getAll('pending'));
    }

    // ---- Queue ----
    async function enqueue(operation) {
        await open();
        operation.createdAt = Date.now();
        operation.status = 'pending';
        operation.retryCount = operation.retryCount || 0;
        operation.clientId = operation.clientId || crypto.randomUUID();
        return promisify(tx('queue', 'readwrite').add(operation));
    }

    async function getQueue() {
        await open();
        return promisify(tx('queue', 'readonly').getAll());
    }

    async function getPendingQueue() {
        await open();
        const idx = tx('queue', 'readonly').index('status');
        return promisify(idx.getAll('pending'));
    }

    async function updateQueueItem(item) {
        await open();
        return promisify(tx('queue', 'readwrite').put(item));
    }

    async function deleteQueueItem(id) {
        await open();
        return promisify(tx('queue', 'readwrite').delete(id));
    }

    async function clearQueue() {
        await open();
        return promisify(tx('queue', 'readwrite').clear());
    }

    // ---- Reference Data ----
    async function saveRefData(type, data) {
        await open();
        return promisify(tx('refdata', 'readwrite').put({ type, data, updatedAt: Date.now() }));
    }

    async function getRefData(type) {
        await open();
        const rec = await promisify(tx('refdata', 'readonly').get(type));
        return rec ? rec.data : null;
    }

    // ---- Metadata ----
    async function setMeta(key, value) {
        await open();
        return promisify(tx('meta', 'readwrite').put({ key, value, updatedAt: Date.now() }));
    }

    async function getMeta(key) {
        await open();
        const rec = await promisify(tx('meta', 'readonly').get(key));
        return rec ? rec.value : null;
    }

    // ---- Cleanup on logout ----
    async function clearAll() {
        await open();
        const storeNames = ['drafts', 'queue', 'refdata', 'meta'];
        const transaction = db.transaction(storeNames, 'readwrite');
        for (const name of storeNames) {
            transaction.objectStore(name).clear();
        }
        return new Promise((resolve, reject) => {
            transaction.oncomplete = resolve;
            transaction.onerror = () => reject(transaction.error);
        });
    }

    // ---- Queue stats ----
    async function getQueueStats() {
        const queue = await getQueue();
        return {
            total: queue.length,
            pending: queue.filter(i => i.status === 'pending').length,
            syncing: queue.filter(i => i.status === 'syncing').length,
            failed: queue.filter(i => i.status === 'failed').length,
        };
    }

    return {
        open,
        // Drafts
        saveDraft, getDraft, getAllDrafts, deleteDraft, getPendingDrafts,
        // Queue
        enqueue, getQueue, getPendingQueue, updateQueueItem, deleteQueueItem, clearQueue,
        // Ref data
        saveRefData, getRefData,
        // Meta
        setMeta, getMeta,
        // Cleanup
        clearAll,
        // Stats
        getQueueStats,
    };
})();
