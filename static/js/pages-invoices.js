/* ============================================
   Invoices List Page — Mobile Card Layout
   ============================================ */
async function renderInvoices() {
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header">
        <h1>فاکتورها</h1>
        <button class="btn btn-primary" onclick="Router.navigate('/invoices/new')">+ فاکتور جدید</button>
      </div>
      <div class="search-bar">
        <input class="form-input" id="invSearch" placeholder="جستجوی فاکتور..." oninput="loadInvoices()" style="flex:2;">
        <input class="form-input jalali-display" id="invDateFrom" readonly placeholder="از تاریخ..."
          onclick="openDateScroller('invDateFrom','invDateFromISO')" style="flex:1;cursor:pointer;">
        <input type="hidden" id="invDateFromISO">
        <input class="form-input jalali-display" id="invDateTo" readonly placeholder="تا تاریخ..."
          onclick="openDateScroller('invDateTo','invDateToISO')" style="flex:1;cursor:pointer;">
        <input type="hidden" id="invDateToISO">
      </div>
      <div id="invoiceContent">
        <div class="loading-skeleton">
          <div class="skel-row"></div><div class="skel-row"></div><div class="skel-row"></div>
        </div>
      </div>
    `);
    loadInvoices();
}

async function loadInvoices() {
    const q = document.getElementById('invSearch')?.value || '';
    const df = document.getElementById('invDateFromISO')?.value || '';
    const dt = document.getElementById('invDateToISO')?.value || '';
    const params = new URLSearchParams();
    if (q) params.set('search', q);
    if (df) params.set('date_from', df);
    if (dt) params.set('date_to', dt);
    try {
        const data = await API.getInvoices(params.toString());
        const results = data.results || data;
        const container = document.getElementById('invoiceContent');
        if (!results.length) {
            container.innerHTML = `
              <div class="empty-state">
                <div class="icon">📄</div>
                <p>هنوز فاکتوری ثبت نشده</p>
                <button class="btn btn-primary" onclick="Router.navigate('/invoices/new')">صدور فاکتور جدید</button>
              </div>`;
            return;
        }
        // Desktop table
        let tableHtml = `
          <div class="table-container desktop-only">
            <table><thead><tr>
              <th>شماره</th><th>مشتری</th><th>تاریخ</th><th>مبلغ</th><th>وضعیت</th><th>عملیات</th>
            </tr></thead><tbody>
            ${results.map(inv => `<tr>
              <td><strong>${escHtml(inv.invoice_number)}</strong></td>
              <td>${escHtml(inv.customer_name || '-')}</td>
              <td>${formatDate(inv.invoice_date)}</td>
              <td><strong>${formatNum(inv.final_amount)} ریال</strong></td>
              <td>${inv.is_paid
                ? '<span class="badge badge-success">پرداخت شده</span>'
                : '<span class="badge badge-warning">پرداخت نشده</span>'}</td>
              <td class="actions-cell" style="white-space:nowrap;">
                <button class="btn btn-sm btn-secondary" onclick="Router.navigate('/invoices/${inv.id}')">ویرایش</button>
                <button class="btn btn-sm btn-accent" onclick="duplicateInv(${inv.id})">کپی</button>
                <button class="btn btn-sm btn-secondary" onclick="printInvoiceById(${inv.id})">🖨️ چاپ</button>
                <button class="btn btn-sm btn-primary" onclick="API.downloadPdf(${inv.id})">PDF</button>
                <button class="btn btn-sm btn-danger" onclick="deleteInv(${inv.id})">حذف</button>
              </td>
            </tr>`).join('')}
            </tbody></table>
          </div>`;

        // Mobile cards
        let cardHtml = `<div class="mobile-cards mobile-only">
          ${results.map(inv => `
            <div class="mobile-card">
              <div class="mobile-card-header">
                <strong>${escHtml(inv.invoice_number)}</strong>
                ${inv.is_paid
                  ? '<span class="badge badge-success">پرداخت شده</span>'
                  : '<span class="badge badge-warning">پرداخت نشده</span>'}
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="card-label">مشتری</span>
                  <span>${escHtml(inv.customer_name || '-')}</span>
                </div>
                <div class="mobile-card-row">
                  <span class="card-label">تاریخ</span>
                  <span>${formatDate(inv.invoice_date)}</span>
                </div>
                <div class="mobile-card-row">
                  <span class="card-label">مبلغ</span>
                  <strong>${formatNum(inv.final_amount)} ریال</strong>
                </div>
              </div>
              <div class="mobile-card-actions">
                <button class="btn btn-sm btn-secondary" onclick="Router.navigate('/invoices/${inv.id}')">ویرایش</button>
                <button class="btn btn-sm btn-secondary" onclick="printInvoiceById(${inv.id})">🖨️</button>
                <button class="btn btn-sm btn-primary" onclick="API.downloadPdf(${inv.id})">PDF</button>
                <button class="btn btn-sm btn-accent" onclick="duplicateInv(${inv.id})">کپی</button>
                <button class="btn btn-sm btn-danger" onclick="deleteInv(${inv.id})">حذف</button>
              </div>
            </div>`).join('')}
        </div>`;

        container.innerHTML = tableHtml + cardHtml;
    } catch (err) { showToast('خطا در بارگذاری', 'error'); }
}

async function duplicateInv(id) {
    try {
        await API.duplicateInvoice(id);
        showToast('فاکتور کپی شد');
        loadInvoices();
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteInv(id) {
    if (!confirm('آیا از حذف این فاکتور مطمئنید؟')) return;
    try {
        await API.deleteInvoice(id);
        showToast('فاکتور حذف شد');
        loadInvoices();
    } catch (err) { showToast(err.message, 'error'); }
}