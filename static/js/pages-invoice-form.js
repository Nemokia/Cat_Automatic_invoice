/* ============================================
   Invoice Form (Create / Edit)
   ============================================ */
let invoiceItems = [];
let invoiceEditId = null;

async function renderInvoiceForm(params) {
    invoiceEditId = params.id === 'new' ? null : params.id;
    invoiceItems = [];

    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header">
        <h1 id="invFormTitle">فاکتور جدید</h1>
        <button class="btn btn-secondary" onclick="Router.navigate('/invoices')">بازگشت</button>
      </div>
      <form id="invoiceForm">
        <div class="invoice-grid">
          <!-- Customer -->
          <div class="card">
            <div class="card-header"><h3>مشتری</h3></div>
            <div class="autocomplete-wrapper">
              <input class="form-input" id="invCustSearch" placeholder="جستجوی مشتری...">
              <div class="autocomplete-list" id="invCustList"></div>
            </div>
            <input type="hidden" id="invCustId">
            <div style="margin-top:8px;font-size:13px;color:var(--text-muted);" id="invCustInfo"></div>
          </div>
          <!-- Dates & Tax -->
          <div class="card">
            <div class="card-header"><h3>تاریخ و مالیات</h3></div>
            <div class="form-group">
              <label>تاریخ فاکتور</label>
              <input class="form-input jalali-display" id="invDate" readonly required placeholder="انتخاب تاریخ..."
                onclick="openDateScroller('invDate', 'invDateISO')" style="cursor:pointer;">
              <input type="hidden" id="invDateISO">
            </div>
            <div class="form-group">
              <label>تاریخ سررسید</label>
              <input class="form-input jalali-display" id="invDue" readonly placeholder="انتخاب تاریخ..."
                onclick="openDateScroller('invDue', 'invDueISO')" style="cursor:pointer;">
              <input type="hidden" id="invDueISO">
            </div>
            <div class="form-group">
              <label>نرخ مالیات فاکتور (%)</label>
              <input class="form-input" id="invTaxRate" type="number" min="0" max="100" value="0" onchange="recalcInvoice()">
            </div>
            <div class="form-group">
              <label>نوع تخفیف</label>
              <select class="form-select" id="invDiscType" onchange="recalcInvoice()">
                <option value="">بدون تخفیف</option>
                <option value="percent">درصد</option>
                <option value="amount">مبلغ</option>
              </select>
            </div>
            <div class="form-group">
              <label>مقدار تخفیف</label>
              <input class="form-input" id="invDiscVal" type="number" min="0" value="0" onchange="recalcInvoice()">
            </div>
          </div>
          <!-- Bank -->
          <div class="card" style="grid-column:1/-1;">
            <div class="card-header"><h3>اطلاعات بانکی</h3></div>
            <div class="invoice-grid">
              <div class="form-group">
                <label>حساب بانکی</label>
                <select class="form-select" id="invBankAcct" onchange="fillBankInfo()">
                  <option value="">انتخاب حساب...</option>
                </select>
              </div>
              <div class="form-group"><label>نام بانک</label><input class="form-input" id="invBankName" readonly></div>
              <div class="form-group"><label>شماره کارت</label><input class="form-input" id="invCard" readonly></div>
              <div class="form-group"><label>شماره شبا</label><input class="form-input" id="invIban" readonly></div>
              <div class="form-group"><label>صاحب حساب</label><input class="form-input" id="invHolder" readonly></div>
            </div>
          </div>
          <!-- Items -->
          <div class="card items-section">
            <div class="card-header">
              <h3>اقلام فاکتور</h3>
              <button class="btn btn-sm btn-primary" type="button" onclick="addInvoiceItem()">+ قلم</button>
            </div>
            <div style="overflow-x:auto;">
              <table class="items-table"><thead><tr>
                <th style="width:30px;">#</th>
                <th>نام کالا</th>
                <th style="width:70px;">تعداد</th>
                <th style="width:100px;">قیمت واحد</th>
                <th style="width:60px;">مالیات%</th>
                <th style="width:90px;">جمع</th>
                <th style="width:30px;"></th>
              </tr></thead><tbody id="invItemsBody"></tbody></table>
            </div>
          </div>
          <!-- Notes & Totals -->
          <div class="card">
            <div class="form-group">
              <label>توضیحات</label>
              <textarea class="form-input" id="invNotes" rows="3"></textarea>
            </div>
            <div class="form-group">
              <label>
                <input type="checkbox" id="invPaid"> پرداخت شده
              </label>
            </div>
          </div>
          <div class="card">
            <div class="totals-box" id="invTotals">
              <div class="totals-row"><span>جمع:</span><span id="tSub">0</span></div>
              <div class="totals-row"><span>مالیات اقلام:</span><span id="tItemTax">0</span></div>
              <div class="totals-row"><span>مالیات فاکتور:</span><span id="tInvTax">0</span></div>
              <div class="totals-row"><span>تخفیف:</span><span id="tDisc">0</span></div>
              <div class="totals-row total"><span>نهایی:</span><span id="tFinal">0</span></div>
            </div>
          </div>
        </div>
        <div style="margin-top:20px;display:flex;gap:10px;">
          <button class="btn btn-primary btn-lg" type="submit">ذخیره فاکتور</button>
          <button class="btn btn-secondary btn-lg" type="button" onclick="Router.navigate('/invoices')">لغو</button>
        </div>
      </form>
    `);

    // Load bank accounts
    try {
        const accts = await API.getBankAccounts();
        const sel = document.getElementById('invBankAcct');
        (accts || []).forEach(a => {
            const opt = document.createElement('option');
            opt.value = a.id;
            opt.textContent = `${a.bank_name} - ${a.card_number}`;
            opt.dataset.data = JSON.stringify(a);
            sel.appendChild(opt);
        });
    } catch (e) {}

    // Customer autocomplete
    attachAutocomplete('invCustSearch', 'invCustList',
        (q) => API.searchCustomers(q),
        (item) => {
            document.getElementById('invCustId').value = item.id;
            document.getElementById('invCustInfo').textContent = `${item.full_name} | ${item.phone || ''}`;
        }
    );

    // If editing, load existing invoice
    if (invoiceEditId) {
        document.getElementById('invFormTitle').textContent = 'ویرایش فاکتور';
        try {
            const inv = await API.getInvoice(invoiceEditId);
            document.getElementById('invCustId').value = inv.customer || '';
            document.getElementById('invCustSearch').value = inv.customer_name || '';
            document.getElementById('invCustInfo').textContent = `${inv.customer_name || ''} | ${inv.customer_phone || ''}`;
            document.getElementById('invDateISO').value = inv.invoice_date || '';
            document.getElementById('invDueISO').value = inv.due_date || '';
            if (inv.invoice_date) {
                const j = Jalali.fromISO(inv.invoice_date);
                document.getElementById('invDate').value = j ? Jalali.format(j) : inv.invoice_date;
            }
            if (inv.due_date) {
                const j = Jalali.fromISO(inv.due_date);
                document.getElementById('invDue').value = j ? Jalali.format(j) : inv.due_date;
            }
            document.getElementById('invTaxRate').value = inv.invoice_tax_rate || 0;
            document.getElementById('invDiscType').value = inv.discount_type || '';
            document.getElementById('invDiscVal').value = inv.discount_value || 0;
            document.getElementById('invNotes').value = inv.notes || '';
            document.getElementById('invPaid').checked = inv.is_paid;
            // Load items
            if (inv.items && inv.items.length) {
                inv.items.forEach(it => {
                    invoiceItems.push({
                        product: it.product, product_name: it.product_name,
                        quantity: it.quantity, unit_price: it.unit_price,
                        tax_rate: it.tax_rate, unit: it.unit, order: it.order
                    });
                });
            }
            renderInvoiceItems();
            recalcInvoice();
        } catch (err) { showToast('خطا در بارگذاری فاکتور', 'error'); }
    } else {
        document.getElementById('invDate').value = Jalali.format(Jalali.today());
        document.getElementById('invDateISO').value = Jalali.toISO(Jalali.today());
        addInvoiceItem();
    }

    document.getElementById('invoiceForm').onsubmit = async (e) => {
        e.preventDefault();
        const payload = {
            customer: document.getElementById('invCustId').value || null,
            invoice_date: document.getElementById('invDateISO').value,
            due_date: document.getElementById('invDueISO').value || null,
            invoice_tax_rate: parseFloat(document.getElementById('invTaxRate').value) || 0,
            discount_type: document.getElementById('invDiscType').value || '',
            discount_value: parseInt(document.getElementById('invDiscVal').value) || 0,
            bank_account: document.getElementById('invBankAcct').value || null,
            notes: document.getElementById('invNotes').value,
            is_paid: document.getElementById('invPaid').checked,
            items: invoiceItems.filter(it => it.product_name.trim()).map((it, idx) => ({
                product: it.product || null,
                product_name: it.product_name,
                quantity: parseFloat(it.quantity) || 1,
                unit_price: parseInt(it.unit_price) || 0,
                tax_rate: parseFloat(it.tax_rate) || 0,
                unit: it.unit || 'عدد',
                order: idx
            }))
        };
        try {
            if (invoiceEditId) {
                await API.updateInvoice(invoiceEditId, payload);
                showToast('فاکتور ویرایش شد');
            } else {
                await API.createInvoice(payload);
                showToast('فاکتور ایجاد شد');
            }
            Router.navigate('/invoices');
        } catch (err) { showToast(err.message, 'error'); }
    };
}

function addInvoiceItem() {
    invoiceItems.push({
        product: null, product_name: '',
        quantity: 1, unit_price: 0, tax_rate: 0, unit: 'عدد', order: invoiceItems.length
    });
    renderInvoiceItems();
}

function removeInvoiceItem(idx) {
    invoiceItems.splice(idx, 1);
    renderInvoiceItems();
    recalcInvoice();
}

function renderInvoiceItems() {
    const tbody = document.getElementById('invItemsBody');
    if (!tbody) return;
    tbody.innerHTML = invoiceItems.map((it, i) => `<tr>
        <td>${i + 1}</td>
        <td>
            <div class="autocomplete-wrapper">
                <input class="form-input" id="itemName${i}" value="${escHtml(it.product_name)}"
                    placeholder="نام کالا..." oninput="onItemInput(${i})"
                    onfocus="onItemInput(${i})">
                <div class="autocomplete-list" id="itemList${i}"></div>
            </div>
        </td>
        <td><input type="number" min="0" step="0.01" value="${it.quantity}" onchange="updateItem(${i},'quantity',this.value)"></td>
        <td><input type="number" min="0" value="${it.unit_price}" onchange="updateItem(${i},'unit_price',this.value)"></td>
        <td><input type="number" min="0" max="100" value="${it.tax_rate}" onchange="updateItem(${i},'tax_rate',this.value)"></td>
        <td class="item-total">${formatNum((parseFloat(it.quantity)||0) * (parseInt(it.unit_price)||0))}</td>
        <td><button class="btn btn-sm btn-danger" type="button" onclick="removeInvoiceItem(${i})">&times;</button></td>
    </tr>`).join('');

    // Attach autocomplete for each item name input
    for (let i = 0; i < invoiceItems.length; i++) {
        attachAutocomplete(`itemName${i}`, `itemList${i}`,
            (q) => API.searchProducts(q),
            (item) => {
                invoiceItems[i].product = item.id;
                invoiceItems[i].product_name = item.name;
                invoiceItems[i].unit_price = item.latest_price || 0;
                invoiceItems[i].unit = item.unit || 'عدد';
                renderInvoiceItems();
                recalcInvoice();
            }
        );
    }
}

let itemInputTimers = {};
function onItemInput(idx) {
    clearTimeout(itemInputTimers[idx]);
    const input = document.getElementById(`itemName${idx}`);
    const list = document.getElementById(`itemList${idx}`);
    if (!input || !list) return;
    const q = input.value.trim();
    if (q.length < 1) { list.classList.remove('show'); return; }
    itemInputTimers[idx] = setTimeout(async () => {
        const items = await API.searchProducts(q);
        if (!items.length) { list.classList.remove('show'); return; }
        list.innerHTML = items.map((it, j) =>
            `<div class="autocomplete-item" data-idx="${j}">${escHtml(it.name)} <span class="sub">${formatNum(it.latest_price)} ریال</span></div>`
        ).join('');
        list.classList.add('show');
        list.querySelectorAll('.autocomplete-item').forEach(el => {
            el.onclick = () => {
                const item = items[+el.dataset.idx];
                invoiceItems[idx].product = item.id;
                invoiceItems[idx].product_name = item.name;
                invoiceItems[idx].unit_price = item.latest_price || 0;
                invoiceItems[idx].unit = item.unit || 'عدد';
                list.classList.remove('show');
                input.value = item.name;
                renderInvoiceItems();
                recalcInvoice();
            };
        });
    }, 250);
}

function updateItem(idx, field, val) {
    invoiceItems[idx][field] = val;
    recalcInvoice();
}

function recalcInvoice() {
    let subtotal = 0, itemTax = 0;
    invoiceItems.forEach(it => {
        const total = (parseFloat(it.quantity) || 0) * (parseInt(it.unit_price) || 0);
        subtotal += total;
        if (parseFloat(it.tax_rate) > 0) {
            itemTax += Math.round(total * parseFloat(it.tax_rate) / 100);
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

    document.getElementById('tSub').textContent = formatNum(subtotal) + ' ریال';
    document.getElementById('tItemTax').textContent = formatNum(itemTax) + ' ریال';
    document.getElementById('tInvTax').textContent = formatNum(invTax) + ' ریال';
    document.getElementById('tDisc').textContent = '-' + formatNum(disc) + ' ریال';
    document.getElementById('tFinal').textContent = formatNum(final_) + ' ریال';
}

function fillBankInfo() {
    const sel = document.getElementById('invBankAcct');
    const opt = sel.options[sel.selectedIndex];
    if (!opt || !opt.dataset.data) return;
    const d = JSON.parse(opt.dataset.data);
    document.getElementById('invBankName').value = d.bank_name || '';
    document.getElementById('invCard').value = d.card_number || '';
    document.getElementById('invIban').value = d.iban || '';
    document.getElementById('invHolder').value = d.account_holder || '';
}
