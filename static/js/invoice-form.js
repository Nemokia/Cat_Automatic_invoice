/* ============================================
   Invoice Form — Items Management
   Minimal JS for: add/remove items, quantity +/-,
   price formatting, autocomplete, recalc totals.
   ============================================ */

let invoiceItems = [];
let itemIdx = 0;

/* Format number with thousand separators */
function fmtNum(n) {
    return Number(n || 0).toLocaleString('fa-IR');
}

/* Format toman (rial / 10) with Persian thousand separators */
function fmtToman(rial) {
    return fmtNum(Math.floor((rial || 0) / 10));
}

/* Parse price from formatted string */
function parsePrice(s) {
    return parseInt(String(s).replace(/[^\d]/g, ''), 10) || 0;
}

/* Add a new invoice item row */
function addInvoiceItem() {
    invoiceItems.push({
        id: itemIdx++,
        product_name: '',
        unit: 'عدد',
        quantity: 1,
        unit_price: 0,
        tax_rate: 0,
        frequency: '',
    });
    renderItems();
}

/* Remove an invoice item */
function removeItem(idx) {
    invoiceItems = invoiceItems.filter(it => it.id !== idx);
    renderItems();
    recalcInvoice();
}

/* Update an item field from input */
function updateItem(idx, field, value) {
    const item = invoiceItems.find(it => it.id === idx);
    if (!item) return;
    if (field === 'quantity' || field === 'unit_price' || field === 'tax_rate') {
        item[field] = parseFloat(value) || 0;
    } else {
        item[field] = value;
    }
    recalcInvoice();
}

/* Handle unit select change: normal selection or + add custom unit */
async function handleUnitChange(idx, select) {
    const val = select.value;
    if (val === '+') {
        const newName = await addCustomUnit(select);
        if (newName) {
            updateItem(idx, 'unit', newName);
            // _unitsCache already updated by addCustomUnit via fetchUnits
        } else {
            // User cancelled — revert to previous value
            const item = invoiceItems.find(it => it.id === idx);
            if (item) select.value = item.unit || '';
        }
    } else {
        updateItem(idx, 'unit', val);
    }
    renderItems();
}

/* Format price input with thousand separators */
function onPriceInput(idx, input) {
    const raw = input.value.replace(/[^\d۰-۹]/g, '');
    const latin = raw.replace(/[۰-۹]/g, d => '۰۱۲۳۴۵۶۷۸۹'.indexOf(d));
    const num = parseInt(latin) || 0;
    const item = invoiceItems.find(it => it.id === idx);
    if (item) item.unit_price = num;
    input.value = num > 0 ? num.toLocaleString('en-US') : '';
    recalcInvoice();
}

/* Render all invoice items into the table */
function renderItems() {
    const tbody = document.getElementById('invItemsBody');
    if (!tbody) return;

    if (invoiceItems.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:20px;">روی «افزودن قلم» کلیک کنید</td></tr>';
        return;
    }

    tbody.innerHTML = invoiceItems.map((it, i) => {
        const total = (it.quantity || 0) * (it.unit_price || 0);
        const isService = it.unit === 'خدمات';
        return `<tr data-item-id="${it.id}">
            <td class="col-num">${i + 1}</td>
            <td class="col-name" data-label="نام کالا">
                <div class="item-row-header">
                    <span class="item-num-badge">${i + 1}</span>
                    <div class="autocomplete-wrapper" style="flex:1;">
                        <input class="form-input" value="${escHtml(it.product_name)}"
                            data-idx="${it.id}" data-field="name"
                            placeholder="نام کالا..."
                            oninput="updateItem(${it.id},'product_name',this.value); searchProducts(${it.id}, this.value)">
                        <div class="autocomplete-list" id="prodList${it.id}"></div>
                    </div>
                    <button type="button" class="btn btn-sm btn-danger item-del-btn" onclick="removeItem(${it.id})" title="حذف">✕</button>
                </div>
            </td>
            <td class="col-unit" data-label="واحد">
                <select class="form-select" onchange="handleUnitChange(${it.id}, this)">${unitOpts(it.unit)}</select>
            </td>
            <td class="col-freq" data-label="دوره">
                <select class="form-select" onchange="updateItem(${it.id},'frequency',this.value)">
                    <option value="">—</option>
                    <option value="hourly"${it.frequency === 'hourly' ? ' selected' : ''}>ساعتی</option>
                    <option value="daily"${it.frequency === 'daily' ? ' selected' : ''}>روزانه</option>
                    <option value="weekly"${it.frequency === 'weekly' ? ' selected' : ''}>هفتگی</option>
                    <option value="monthly"${it.frequency === 'monthly' ? ' selected' : ''}>ماهانه</option>
                    <option value="yearly"${it.frequency === 'yearly' ? ' selected' : ''}>سالانه</option>
                </select>
            </td>
            <td class="col-qty" data-label="تعداد">
                <input type="number" min="0.01" step="0.01" value="${it.quantity}"
                    onchange="updateItem(${it.id},'quantity',this.value)" class="qty-input">
            </td>
            <td class="col-price" data-label="قیمت واحد">
                <input class="form-input price-input"
                    value="${it.unit_price > 0 ? it.unit_price.toLocaleString('en-US') : ''}"
                    oninput="onPriceInput(${it.id}, this)"
                    placeholder="0" inputmode="numeric" dir="ltr" style="text-align:left;">
            </td>
            <td class="col-tax" data-label="مالیات %">
                <input type="number" min="0" max="100" step="0.01" value="${it.tax_rate}"
                    onchange="updateItem(${it.id},'tax_rate',this.value)">
            </td>
            <td class="col-total" data-label="جمع">
                <span class="item-total">${fmtNum(total)}</span>
            </td>
            <td class="col-action" data-label="">
                <button type="button" class="btn btn-sm btn-danger" onclick="removeItem(${it.id})" title="حذف">✕</button>
            </td>
        </tr>`;
    }).join('');
    updateFreqHeader();
}

/* Show/hide the frequency column header + cells based on whether any item uses 'خدمات' */
function updateFreqHeader() {
    const hasService = invoiceItems.some(it => it.unit === 'خدمات');
    const th = document.querySelector('.items-table th.col-freq');
    if (th) th.style.display = hasService ? '' : 'none';
    document.querySelectorAll('.items-table td.col-freq').forEach(td => {
        td.style.display = hasService ? '' : 'none';
    });
}

/* Recalculate invoice totals */
function recalcInvoice() {
    let subtotal = 0, itemTax = 0;
    invoiceItems.forEach(it => {
        const total = (it.quantity || 0) * (it.unit_price || 0);
        subtotal += total;
        if (it.tax_rate > 0) {
            itemTax += Math.round(total * it.tax_rate / 100);
        }
    });

    const taxRate = parseFloat(document.getElementById('invTaxRate')?.value) || 0;
    const invTax = Math.round(subtotal * taxRate / 100);
    const discType = document.getElementById('invDiscType')?.value;
    const discVal = parseInt(document.getElementById('invDiscVal')?.value) || 0;
    let disc = 0;
    if (discType === 'percent') disc = Math.round(subtotal * discVal / 100);
    else if (discType === 'amount') disc = discVal;

    const final_ = Math.max(0, subtotal + itemTax + invTax - disc);

    document.getElementById('tSubtotal').innerHTML = fmtNum(subtotal) + ' ریال<br><small class="toman">' + fmtToman(subtotal) + ' تومان</small>';
    document.getElementById('tItemTax').innerHTML = fmtNum(itemTax) + ' ریال<br><small class="toman">' + fmtToman(itemTax) + ' تومان</small>';
    document.getElementById('tInvTax').innerHTML = fmtNum(invTax) + ' ریال<br><small class="toman">' + fmtToman(invTax) + ' تومان</small>';
    document.getElementById('tDiscount').innerHTML = fmtNum(disc) + ' ریال<br><small class="toman">' + fmtToman(disc) + ' تومان</small>';
    document.getElementById('tFinal').innerHTML = fmtNum(final_) + ' ریال<br><small class="toman">' + fmtToman(final_) + ' تومان</small>';
}

/* Fill bank info from saved account selection */
function fillBankInfo() {
    const sel = document.getElementById('invBankAcct');
    const opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.dataset.bank_name) {
        document.getElementById('invBankName').value = '';
        document.getElementById('invCard').value = '';
        document.getElementById('invIban').value = '';
        document.getElementById('invHolder').value = '';
        return;
    }
    document.getElementById('invBankName').value = opt.dataset.bank_name || '';
    document.getElementById('invCard').value = opt.dataset.card_number || '';
    document.getElementById('invIban').value = opt.dataset.iban || '';
    document.getElementById('invHolder').value = opt.dataset.account_holder || '';
}

/* Product autocomplete for item name */
let productTimers = {};
function searchProducts(idx, q) {
    clearTimeout(productTimers[idx]);
    const list = document.getElementById(`prodList${idx}`);
    if (!list) return;
    q = (q || '').trim();
    if (q.length < 1) { list.classList.remove('show'); return; }

    productTimers[idx] = setTimeout(async () => {
        try {
            const res = await fetch(`/search/products/?q=${encodeURIComponent(q)}`, {
                headers: { 'X-CSRFToken': getCsrfToken() }
            });
            const items = await res.json();
            if (!items.length) { list.classList.remove('show'); return; }

            list.innerHTML = items.map((p, i) =>
                `<div class="autocomplete-item" data-idx="${i}" onclick="pickProduct(${idx}, ${JSON.stringify(p).replace(/"/g, '&quot;')})">${escHtml(p.name)} — ${fmtNum(p.price)} ریال</div>`
            ).join('');
            list.classList.add('show');
        } catch (e) { list.classList.remove('show'); }
    }, 200);
}

function pickProduct(idx, product) {
    const item = invoiceItems.find(it => it.id === idx);
    if (!item) return;
    item.product_name = product.name;
    item.unit_price = parseInt(product.price) || 0;
    item.unit = product.unit || 'عدد';
    item.frequency = product.frequency || '';
    const list = document.getElementById(`prodList${idx}`);
    if (list) list.classList.remove('show');
    renderItems();
    recalcInvoice();
}

/* Customer autocomplete */
let custTimer;
function searchCustomers(field, q) {
    clearTimeout(custTimer);
    const listId = field === 'name' ? 'invCustNameList' : 'invCustPhoneList';
    const list = document.getElementById(listId);
    if (!list) return;
    q = (q || '').trim();
    if (q.length < 1) { list.classList.remove('show'); return; }

    custTimer = setTimeout(async () => {
        try {
            const res = await fetch(`/search/customers/?q=${encodeURIComponent(q)}`, {
                headers: { 'X-CSRFToken': getCsrfToken() }
            });
            const items = await res.json();
            if (!items.length) { list.classList.remove('show'); return; }

            list.innerHTML = items.map((c, i) =>
                `<div class="autocomplete-item" onclick="pickCustomer(${JSON.stringify(c).replace(/"/g, '&quot;')})">${escHtml(c.full_name)} — ${escHtml(c.phone || '')}</div>`
            ).join('');
            list.classList.add('show');
        } catch (e) { list.classList.remove('show'); }
    }, 200);
}

function pickCustomer(c) {
    document.getElementById('invCustName').value = c.full_name || '';
    document.getElementById('invCustPhone').value = c.phone || '';
    document.getElementById('invCustAddress').value = c.address || '';
    document.getElementById('invCustId').value = c.id || '';
    document.getElementById('invCustNameList').classList.remove('show');
    document.getElementById('invCustPhoneList').classList.remove('show');
}

/* Bank account autocomplete */
let bankTimer;
function searchBankAccounts(field, q) {
    clearTimeout(bankTimer);
    const listId = field === 'name' ? 'invBankNameList' : field === 'card' ? 'invCardList' : 'invHolderList';
    const list = document.getElementById(listId);
    if (!list) return;
    q = (q || '').trim();

    bankTimer = setTimeout(async () => {
        try {
            const res = await fetch(`/search/bank-accounts/?q=${encodeURIComponent(q)}`, {
                headers: { 'X-CSRFToken': getCsrfToken() }
            });
            const items = await res.json();
            if (!items.length) { list.classList.remove('show'); return; }

            list.innerHTML = items.map((a, i) =>
                `<div class="autocomplete-item" onclick="pickBankAccount(${JSON.stringify(a).replace(/\"/g, '&quot;')})">${escHtml(a.bank_name)} — ${escHtml(a.card_number)} <span class="sub">${escHtml(a.account_holder)}</span></div>`
            ).join('');
            list.classList.add('show');
        } catch (e) { list.classList.remove('show'); }
    }, 200);
}

function pickBankAccount(a) {
    document.getElementById('invBankName').value = a.bank_name || '';
    document.getElementById('invCard').value = a.card_number || '';
    document.getElementById('invHolder').value = a.account_holder || '';
    document.getElementById('invIban').value = a.iban || '';
    document.getElementById('invBankNameList').classList.remove('show');
    document.getElementById('invCardList').classList.remove('show');
    document.getElementById('invHolderList').classList.remove('show');
}

/* ============================================================
   Save & Share — submit the invoice form via AJAX, then share
   the invoice PDF (not the HTML page). Stays on the form page.
   ============================================================ */

async function submitAndShare(form, submitBtn) {
    submitBtn.disabled = true;
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '⏳ در حال ذخیره...';
    try {
        const shareUrl = (form.getAttribute('action') || window.location.href).split('?')[0] +
                         '?share=1';
        const res = await fetch(shareUrl, {
            method: 'POST',
            body: new FormData(form),
            headers: {
                'X-CSRFToken': getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json',
            },
            credentials: 'same-origin',
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
            showToast((data.errors && data.errors.join(' ')) || 'خطا در ذخیره فاکتور', 'error');
            return;
        }
        showToast('فاکتور ذخیره شد — آماده ارسال');
        await shareInvoicePdfFile(data.invoice_number, data.pdf_url);
    } catch (err) {
        showToast(err.message || 'خطا در ذخیره و ارسال', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalText;
    }
}

/* Share the actual PDF file via Web Share API; fallbacks below */
async function shareInvoicePdfFile(invoiceNumber, pdfUrl) {
    const fileName = `${invoiceNumber || 'invoice'}.pdf`;
    try {
        const resp = await fetch(pdfUrl, { credentials: 'same-origin' });
        if (!resp.ok) throw new Error('خطا در دریافت PDF');
        const blob = await resp.blob();
        const file = new File([blob], fileName, { type: 'application/pdf' });

        // Level 2: share the actual PDF file (messengers pick it up)
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({ files: [file], title: fileName, text: 'فاکتور فروش' });
            return;
        }
        // Level 1: share the PDF link
        if (navigator.share) {
            await navigator.share({
                title: fileName,
                text: 'فاکتور فروش',
                url: new URL(pdfUrl, window.location.origin).href,
            });
            return;
        }
        // Desktop fallback: open the PDF in a new tab (user attaches manually)
        window.open(pdfUrl, '_blank');
        showToast('اشتراک‌گذاری مستقیم پشتیبانی نمی‌شود؛ PDF در تب جدید باز شد');
    } catch (err) {
        if (err && err.name === 'AbortError') return; // user closed share sheet
        showToast(err.message || 'خطا در اشتراک‌گذاری', 'error');
    }
}

/* Serialize items to hidden inputs before form submit */
function prepareInvoiceSubmit(e) {
    // Remove any previously injected item inputs
    e.target.querySelectorAll('.injected-item-field').forEach(el => el.remove());

    invoiceItems.filter(it => it.product_name.trim()).forEach((it, i) => {
        const fields = {
            'item_product_name[]': it.product_name,
            'item_quantity[]': it.quantity,
            'item_unit_price[]': it.unit_price,
            'item_tax_rate[]': it.tax_rate,
            'item_unit[]': it.unit,
            'item_frequency[]': it.frequency,
        };
        Object.entries(fields).forEach(([name, value]) => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = name;
            input.value = value;
            input.className = 'injected-item-field';
            e.target.appendChild(input);
        });
    });
}

/* Helper: HTML escape */
function escHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

/* Helper: unit select options */
let _unitsCache = null;
function unitOpts(selected) {
    const units = _unitsCache || PREDEFINED_UNITS;
    let html = '<option value="">انتخاب واحد...</option>';
    units.forEach(u => {
        html += `<option value="${escHtml(u)}"${u === selected ? ' selected' : ''}>${escHtml(u)}</option>`;
    });
    html += '<option value="+">+ افزودن واحد جدید</option>';
    return html;
}

/* Helper: CSRF token */
function getCsrfToken() {
    const cookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    return cookie ? cookie.split('=')[1] : '';
}
