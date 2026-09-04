/* ============================================
   Unit Select — custom dropdown with add/delete
   Predefined + per-user custom units.
   Custom units show a trash icon for deletion.
   ============================================ */
const PREDEFINED_UNITS = ['عدد', 'کیلوگرم', 'گرم', 'لیتر', 'خدمات', 'مسافت'];

async function fetchUnits() {
    try {
        const r = await fetch('/units/', { headers: { 'X-CSRFToken': getCsrfToken() } });
        return await r.json();
    } catch (e) { return PREDEFINED_UNITS; }
}

/**
 * Initialize a custom unit dropdown inside `containerEl` (a <div>).
 * A hidden <input> named `inputName` is created for form submission.
 * Returns a promise that resolves when units are loaded.
 */
async function initUnitSelect(containerEl, selected, inputName) {
    const units = await fetchUnits();
    const hiddenInput = document.createElement('input');
    hiddenInput.type = 'hidden';
    hiddenInput.name = inputName || 'unit';
    hiddenInput.value = selected || '';
    containerEl.appendChild(hiddenInput);

    const wrapper = document.createElement('div');
    wrapper.className = 'unit-dropdown-wrapper';
    containerEl.appendChild(wrapper);

    // Main button
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'unit-dropdown-btn';
    wrapper.appendChild(btn);

    // Dropdown list
    const list = document.createElement('div');
    list.className = 'unit-dropdown-list';
    wrapper.appendChild(list);

    function render(unitsArr, val) {
        list.innerHTML = '';
        unitsArr.forEach(u => {
            const row = document.createElement('div');
            row.className = 'unit-dropdown-item';
            if (u === val) row.classList.add('active');

            const label = document.createElement('span');
            label.className = 'unit-dropdown-label';
            label.textContent = u;
            row.appendChild(label);

            // Trash icon only for custom (non-predefined) units
            if (!PREDEFINED_UNITS.includes(u)) {
                const trash = document.createElement('span');
                trash.className = 'unit-dropdown-trash';
                trash.innerHTML = '🗑';
                trash.title = 'حذف واحد';
                trash.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (!confirm(`واحد «${u}» حذف شود؟`)) return;
                    const newUnits = await _deleteUnitFromDB(u);
                    if (newUnits) {
                        // If the deleted unit was selected, clear selection
                        if (hiddenInput.value === u) {
                            hiddenInput.value = '';
                        }
                        render(newUnits, hiddenInput.value);
                    }
                });
                row.appendChild(trash);
            }

            row.addEventListener('click', () => {
                hiddenInput.value = u;
                btn.textContent = u;
                list.classList.remove('open');
                wrapper.classList.remove('open');
            });
            list.appendChild(row);
        });

        // "+ افزودن واحد جدید" option
        const addRow = document.createElement('div');
        addRow.className = 'unit-dropdown-item unit-dropdown-add';
        addRow.textContent = '+ افزودن واحد جدید';
        addRow.addEventListener('click', async (e) => {
            e.stopPropagation();
            list.classList.remove('open');
            wrapper.classList.remove('open');
            const newName = await _showUnitModal();
            if (newName) {
                const newUnits = await _addUnitToDB(newName);
                if (newUnits) {
                    hiddenInput.value = newName;
                    render(newUnits, newName);
                }
            }
        });
        list.appendChild(addRow);

        // Update button text
        btn.textContent = (val && unitsArr.includes(val)) ? val : 'انتخاب واحد...';
    }

    render(units, selected || '');

    // Toggle dropdown
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = list.classList.contains('open');
        // Close all other open dropdowns first
        document.querySelectorAll('.unit-dropdown-list.open').forEach(l => {
            l.classList.remove('open');
            l.parentElement.classList.remove('open');
        });
        if (!isOpen) {
            list.classList.add('open');
            wrapper.classList.add('open');
        }
    });

    // Close on outside click
    document.addEventListener('click', () => {
        list.classList.remove('open');
        wrapper.classList.remove('open');
    });
    list.addEventListener('click', (e) => e.stopPropagation());
}

/* ── Modal for new unit name ── */
function _ensureUnitModal() {
    if (document.getElementById('unitModal')) return;
    const overlay = document.createElement('div');
    overlay.id = 'unitModal';
    overlay.className = 'unit-modal-overlay';
    overlay.innerHTML = `
    <div class="unit-modal-box">
        <h3>افزودن واحد جدید</h3>
        <input id="unitModalInput" class="form-input" placeholder="نام واحد را وارد کنید..." autofocus />
        <div class="unit-modal-actions">
            <button id="unitModalOk" class="btn btn-primary">تأیید</button>
            <button id="unitModalCancel" class="btn btn-secondary">انصراف</button>
        </div>
    </div>`;
    document.body.appendChild(overlay);

    const input  = document.getElementById('unitModalInput');
    const okBtn  = document.getElementById('unitModalOk');
    const canBtn = document.getElementById('unitModalCancel');

    function close() { overlay.style.display = 'none'; input.value = ''; }
    canBtn.onclick = close;
    overlay.onclick = function(e) { if (e.target === overlay) close(); };

    okBtn.onclick = function() {
        const name = input.value.trim();
        if (!name) { input.focus(); return; }
        overlay.style.display = 'none';
        input.value = '';
        if (overlay._resolve) overlay._resolve(name);
    };

    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); okBtn.click(); }
        if (e.key === 'Escape') { close(); if (overlay._resolve) overlay._resolve(null); }
    });
}

/* Show modal, return unit name or null */
function _showUnitModal() {
    _ensureUnitModal();
    const overlay = document.getElementById('unitModal');
    const input   = document.getElementById('unitModalInput');
    return new Promise(resolve => {
        overlay._resolve = resolve;
        overlay.style.display = 'flex';
        setTimeout(() => { input.value = ''; input.focus(); }, 50);
    });
}

/* Add unit to DB, return full units list or null */
async function _addUnitToDB(name) {
    const fd = new FormData();
    fd.append('name', name);
    try {
        const r = await fetch('/units/add/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: fd
        });
        return await r.json();
    } catch (e) { return null; }
}

/* Delete unit from DB, return full units list or null */
async function _deleteUnitFromDB(name) {
    const fd = new FormData();
    fd.append('name', name);
    try {
        const r = await fetch('/units/delete/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: fd
        });
        return await r.json();
    } catch (e) { return null; }
}

/* ── Legacy API: keep for backward compatibility ── */
/* Prompt for new unit name via modal, add to DB, refresh select.
   Returns the new unit name if added, null if cancelled. */
async function addCustomUnit(select) {
    const newName = await _showUnitModal();
    if (!newName) return null;
    await _addUnitToDB(newName);
    // Refresh global cache so invoice-form.js renderItems picks up the new unit
    const units = await fetchUnits();
    if (typeof _unitsCache !== 'undefined') _unitsCache = units;
    // If `select` is an old-style <select>, rebuild its options
    if (select && select.tagName === 'SELECT') {
        select.innerHTML = '<option value="">انتخاب واحد...</option>';
        units.forEach(u => {
            const opt = document.createElement('option');
            opt.value = u; opt.textContent = u;
            if (u === newName) opt.selected = true;
            select.appendChild(opt);
        });
        const plus = document.createElement('option');
        plus.value = '+'; plus.textContent = '+ افزودن واحد جدید';
        select.appendChild(plus);
    }
    return newName;
}

/* Delete a custom unit (only non-predefined) */
async function deleteCustomUnit(name, callback) {
    const fd = new FormData();
    fd.append('name', name);
    try {
        await fetch('/units/delete/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCsrfToken() },
            body: fd
        });
        if (callback) callback();
    } catch (e) {}
}
