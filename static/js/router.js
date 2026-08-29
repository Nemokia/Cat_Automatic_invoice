/* ============================================
   Simple Hash Router
   ============================================ */
const Router = {
    routes: {},
    current: null,

    register(path, handler) {
        this.routes[path] = handler;
    },

    navigate(path) {
        window.location.hash = path;
    },

    init() {
        window.addEventListener('hashchange', () => this.resolve());
        this.resolve();
    },

    resolve() {
        const hash = window.location.hash.slice(1) || '/';
        const parts = hash.split('/').filter(Boolean);

        // Auth check
        if (!API.isLoggedIn() && hash !== '/login' && hash !== '/register') {
            this.navigate('/login');
            return;
        }

        // Find matching route
        let handler = null;
        let params = {};

        for (const [pattern, h] of Object.entries(this.routes)) {
            const patternParts = pattern.split('/').filter(Boolean);
            if (patternParts.length !== parts.length) continue;

            let match = true;
            const p = {};
            for (let i = 0; i < patternParts.length; i++) {
                if (patternParts[i].startsWith(':')) {
                    p[patternParts[i].slice(1)] = parts[i];
                } else if (patternParts[i] !== parts[i]) {
                    match = false;
                    break;
                }
            }
            if (match) { handler = h; params = p; break; }
        }

        if (handler) {
            this.current = { path: hash, params };
            handler(params);
        } else {
            this.navigate('/');
        }
    }
};
