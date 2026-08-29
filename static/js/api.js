/* ============================================
   API Client - Cat_Automatic_invoice
   ============================================ */
const API = {
    BASE: '/api',
    token: localStorage.getItem('access_token'),
    refresh: localStorage.getItem('refresh_token'),

    async request(method, path, data = null, isFormData = false) {
        const headers = {};
        if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
        if (!isFormData) headers['Content-Type'] = 'application/json';

        const opts = { method, headers };
        if (data) {
            opts.body = isFormData ? data : JSON.stringify(data);
        }

        let res = await fetch(`${this.BASE}${path}`, opts);

        // Token expired - try refresh
        if (res.status === 401 && this.refresh) {
            const refreshed = await this.refreshToken();
            if (refreshed) {
                headers['Authorization'] = `Bearer ${this.token}`;
                res = await fetch(`${this.BASE}${path}`, { ...opts, headers });
            }
        }

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            const msg = err.detail || err.non_field_errors?.[0] || Object.values(err).flat().join(', ') || 'خطای سرور';
            throw new Error(msg);
        }

        if (res.status === 204) return null;
        return res.json();
    },

    async refreshToken() {
        try {
            const res = await fetch(`${this.BASE}/token/refresh/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh: this.refresh })
            });
            if (!res.ok) { this.logout(); return false; }
            const data = await res.json();
            this.setTokens(data.access, data.refresh);
            return true;
        } catch { this.logout(); return false; }
    },

    setTokens(access, refresh) {
        this.token = access;
        this.refresh = refresh;
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
    },

    clearTokens() {
        this.token = null;
        this.refresh = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    },

    logout() {
        this.clearTokens();
        localStorage.removeItem('user');
        window.location.hash = '#/login';
    },

    isLoggedIn() { return !!this.token; },

    getUser() {
        try { return JSON.parse(localStorage.getItem('user')); }
        catch { return null; }
    },

    setUser(user) {
        localStorage.setItem('user', JSON.stringify(user));
    },

    // Auth
    login: (data) => API.request('POST', '/auth/login/', data),
    register: (data) => API.request('POST', '/auth/register/', data),
    getProfile: () => API.request('GET', '/auth/profile/'),
    updateProfile: (data) => API.request('PATCH', '/auth/profile/', data),
    getSellerProfile: () => API.request('GET', '/auth/seller-profile/'),
    updateSellerProfile: (data) => API.request('PATCH', '/auth/seller-profile/', data),
    changePassword: (data) => API.request('POST', '/auth/change-password/', data),
    getDashboard: () => API.request('GET', '/auth/dashboard/'),

    // Customers
    getCustomers: (q) => API.request('GET', `/customers/?search=${q||''}`),
    getCustomer: (id) => API.request('GET', `/customers/${id}/`),
    createCustomer: (data) => API.request('POST', '/customers/', data),
    updateCustomer: (id, data) => API.request('PATCH', `/customers/${id}/`, data),
    deleteCustomer: (id) => API.request('DELETE', `/customers/${id}/`),
    searchCustomers: (q) => API.request('GET', `/customers/autocomplete/?q=${q}`),

    // Products
    getProducts: (q) => API.request('GET', `/products/?search=${q||''}`),
    getProduct: (id) => API.request('GET', `/products/${id}/`),
    createProduct: (data) => API.request('POST', '/products/', data),
    updateProduct: (id, data) => API.request('PATCH', `/products/${id}/`, data),
    deleteProduct: (id) => API.request('DELETE', `/products/${id}/`),
    searchProducts: (q) => API.request('GET', `/products/autocomplete/?q=${q}`),
    addPrice: (id, data) => API.request('POST', `/products/${id}/price/`, data),

    // Invoices
    getInvoices: (params) => API.request('GET', `/invoices/?${params||''}`),
    getInvoice: (id) => API.request('GET', `/invoices/${id}/`),
    createInvoice: (data) => API.request('POST', '/invoices/', data),
    updateInvoice: (id, data) => API.request('PATCH', `/invoices/${id}/`, data),
    deleteInvoice: (id) => API.request('DELETE', `/invoices/${id}/`),
    duplicateInvoice: (id) => API.request('POST', `/invoices/${id}/duplicate/`),

    // Banks
    getBanks: () => API.request('GET', '/banks/list/'),
    getBankAccounts: () => API.request('GET', '/banks/accounts/?select=1'),
    createBankAccount: (data) => API.request('POST', '/banks/accounts/', data),
    updateBankAccount: (id, data) => API.request('PATCH', `/banks/accounts/${id}/`, data),
    deleteBankAccount: (id) => API.request('DELETE', `/banks/accounts/${id}/`),

    // Reports
    getSalesReport: (params) => API.request('GET', `/reports/sales/?${params||''}`),
    getCustomerReport: () => API.request('GET', '/reports/customers/'),
    getProductReport: () => API.request('GET', '/reports/products/'),

    // Export
    exportExcel: (params) => {
        window.open(`/api/export/excel/?${params}`, '_blank');
    },

    // PDF
    downloadPdf: (id) => {
        window.open(`/api/pdf/${id}/`, '_blank');
    }
};
