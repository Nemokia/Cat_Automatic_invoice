/* ============================================
   Invoices List Page
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
      <div class="table-container">
        <table><thead><tr>
          <th>شماره</th><th>مشتری</th><th>تاریخ</th><th>مبلغ</th><th>وضعیت</th><th>عملیات</th>
        </tr></thead><tbody id="invBody"></tbody></table>
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
        const tbody = document.getElementById('invBody');
        if (!results.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">فاکتوری یافت نشد</td></tr>';
            return;
        }
        tbody.innerHTML = results.map(inv => `<tr>
            <td><strong>${escHtml(inv.invoice_number)}</strong></td>
            <td>${escHtml(inv.customer_name || '-')}</td>
            <td>${formatDate(inv.invoice_date)}</td>
            <td>${formatNum(inv.final_amount)} ریال</td>
            <td>${inv.is_paid
                ? '<span class="badge badge-success">پرداخت شده</span>'
                : '<span class="badge badge-warning">پرداخت نشده</span>'}</td>
            <td style="white-space:nowrap;">
              <button class="btn btn-sm btn-secondary" onclick="Router.navigate('/invoices/${inv.id}')">ویرایش</button>
              <button class="btn btn-sm btn-accent" onclick="duplicateInv(${inv.id})">کپی</button>
              <button class="btn btn-sm btn-secondary" onclick="printInvoiceById(${inv.id})">🖨️ چاپ</button>
              <button class="btn btn-sm btn-primary" onclick="API.downloadPdf(${inv.id})">PDF</button>
              <button class="btn btn-sm btn-danger" onclick="deleteInv(${inv.id})">حذف</button>
            </td>
        </tr>`).join('');
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
