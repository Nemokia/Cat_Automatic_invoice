/* ============================================
   Utility Functions
   ============================================ */
function showToast(msg, type = 'success') {
    const c = document.getElementById('toasts');
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.textContent = msg;
    c.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

function formatNum(n) {
    return Number(n || 0).toLocaleString('fa-IR');
}

function formatDate(d) {
    if (!d) return '-';
    return new Date(d).toLocaleDateString('fa-IR');
}

function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

/* Autocomplete: attach to an input, call searchFn(q), pickCallback(item) */
function attachAutocomplete(inputId, listId, searchFn, pickCallback) {
    const input = document.getElementById(inputId);
    const list = document.getElementById(listId);
    if (!input || !list) return;
    let timer = null;
    let items = [];
    let idx = -1;

    input.addEventListener('input', () => {
        clearTimeout(timer);
        const q = input.value.trim();
        if (q.length < 1) { list.classList.remove('show'); return; }
        timer = setTimeout(async () => {
            items = await searchFn(q);
            idx = -1;
            if (!items.length) { list.classList.remove('show'); return; }
            list.innerHTML = items.map((it, i) =>
                `<div class="autocomplete-item" data-idx="${i}">${escHtml(it.full_name || it.name || '')} <span class="sub">${escHtml(it.phone || it.unit || '')}</span></div>`
            ).join('');
            list.classList.add('show');
            list.querySelectorAll('.autocomplete-item').forEach(el => {
                el.onclick = () => {
                    const item = items[+el.dataset.idx];
                    pickCallback(item);
                    list.classList.remove('show');
                    input.value = item.full_name || item.name || '';
                };
            });
        }, 250);
    });

    input.addEventListener('blur', () => {
        setTimeout(() => list.classList.remove('show'), 200);
    });

    input.addEventListener('keydown', (e) => {
        if (!list.classList.contains('show')) return;
        if (e.key === 'ArrowDown') { idx = Math.min(idx + 1, items.length - 1); updateSel(); e.preventDefault(); }
        if (e.key === 'ArrowUp') { idx = Math.max(idx - 1, 0); updateSel(); e.preventDefault(); }
        if (e.key === 'Enter' && idx >= 0) { items[idx] && pickCallback(items[idx]); list.classList.remove('show'); e.preventDefault(); }
    });

    function updateSel() {
        list.querySelectorAll('.autocomplete-item').forEach((el, i) => {
            el.classList.toggle('selected', i === idx);
        });
    }
}

function openModal(id) { document.getElementById(id)?.classList.add('show'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('show'); }
