/* ============================================
   Reports Page
   ============================================ */
async function renderReports() {
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header"><h1>گزارش‌ها</h1></div>
      <div class="tabs">
        <button class="tab-btn active" onclick="showReportTab('sales',this)">فروش</button>
        <button class="tab-btn" onclick="showReportTab('customers',this)">مشتریان</button>
        <button class="tab-btn" onclick="showReportTab('products',this)">محصولات</button>
      </div>
      <div id="reportContent"></div>
    `);
    showReportTab('sales', document.querySelector('.tab-btn'));
}

async function showReportTab(tab, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const c = document.getElementById('reportContent');

    if (tab === 'sales') {
        c.innerHTML = `
          <div class="search-bar">
            <input class="form-input jalali-display" id="rptFrom" readonly placeholder="از تاریخ..."
              onclick="openDateScroller('rptFrom','rptFromISO')" style="flex:1;cursor:pointer;">
            <input type="hidden" id="rptFromISO">
            <input class="form-input jalali-display" id="rptTo" readonly placeholder="تا تاریخ..."
              onclick="openDateScroller('rptTo','rptToISO')" style="flex:1;cursor:pointer;">
            <input type="hidden" id="rptToISO">
            <button class="btn btn-primary" onclick="loadSalesReport()">نمایش</button>
            <button class="btn btn-accent" onclick="exportSales()">دانلود Excel</button>
          </div>
          <div class="stats-grid" id="salesStats"></div>
          <div class="card">
            <div class="card-header"><h3>گزارش ماهانه</h3></div>
            <div class="table-container">
              <table><thead><tr><th>ماه</th><th>تعداد</th><th>مجموع</th></tr></thead>
              <tbody id="salesMonthly"></tbody></table>
            </div>
          </div>`;
        loadSalesReport();
    } else if (tab === 'customers') {
        c.innerHTML = `
          <div class="card">
            <div class="card-header"><h3>گزارش مشتریان</h3></div>
            <div class="table-container">
              <table><thead><tr><th>نام</th><th>تلفن</th><th>تعداد فاکتور</th><th>مجموع خرید</th></tr></thead>
              <tbody id="rptCustBody"></tbody></table>
            </div>
          </div>`;
        try {
            const data = await API.getCustomerReport();
            const tbody = document.getElementById('rptCustBody');
            if (!data.length) { tbody.innerHTML = '<tr><td colspan="4" class="empty-state">داده‌ای نیست</td></tr>'; return; }
            tbody.innerHTML = data.map(c => `<tr>
                <td><strong>${escHtml(c.name)}</strong></td>
                <td>${escHtml(c.phone || '-')}</td>
                <td>${c.num_invoices}</td>
                <td>${formatNum(c.total_spent)} ریال</td>
            </tr>`).join('');
        } catch (err) { showToast('خطا در بارگذاری', 'error'); }
    } else if (tab === 'products') {
        c.innerHTML = `
          <div class="card">
            <div class="card-header"><h3>گزارش محصولات</h3></div>
            <div class="table-container">
              <table><thead><tr><th>نام</th><th>قیمت</th><th>دفعات فروش</th><th>درآمد</th></tr></thead>
              <tbody id="rptProdBody"></tbody></table>
            </div>
          </div>`;
        try {
            const data = await API.getProductReport();
            const tbody = document.getElementById('rptProdBody');
            if (!data.length) { tbody.innerHTML = '<tr><td colspan="4" class="empty-state">داده‌ای نیست</td></tr>'; return; }
            tbody.innerHTML = data.map(p => `<tr>
                <td><strong>${escHtml(p.name)}</strong></td>
                <td>${formatNum(p.latest_price)} ریال</td>
                <td>${p.times_sold}</td>
                <td>${formatNum(p.total_revenue)} ریال</td>
            </tr>`).join('');
        } catch (err) { showToast('خطا در بارگذاری', 'error'); }
    }
}

async function loadSalesReport() {
    const from = document.getElementById('rptFromISO')?.value || '';
    const to = document.getElementById('rptToISO')?.value || '';
    const params = new URLSearchParams();
    if (from) params.set('date_from', from);
    if (to) params.set('date_to', to);
    try {
        const data = await API.getSalesReport(params.toString());
        const s = data.summary || {};
        document.getElementById('salesStats').innerHTML = `
            <div class="stat-card"><div class="label">تعداد فاکتور</div><div class="value">${formatNum(s.invoice_count)}</div></div>
            <div class="stat-card accent"><div class="label">مجموع فروش</div><div class="value">${formatNum(s.total_sales)} ریال</div></div>
            <div class="stat-card green"><div class="label">مالیات</div><div class="value">${formatNum((s.total_tax||0) + (s.total_invoice_tax||0))} ریال</div></div>
            <div class="stat-card red"><div class="label">تخفیف</div><div class="value">${formatNum(s.total_discount)} ریال</div></div>`;

        const monthly = data.monthly || [];
        const tbody = document.getElementById('salesMonthly');
        if (!monthly.length) { tbody.innerHTML = '<tr><td colspan="3" class="empty-state">داده‌ای نیست</td></tr>'; return; }
        tbody.innerHTML = monthly.map(m => {
            // Convert Gregorian month start to Jalali for display
            const gDate = `${m.invoice_date__year}-${String(m.invoice_date__month).padStart(2,'0')}-01`;
            const j = Jalali.fromISO(gDate);
            const label = j ? `${faNum(j.jy)}/${faNum(String(j.jm).padStart(2,'0'))}` : `${m.invoice_date__year}/${m.invoice_date__month}`;
            return `<tr>
            <td>${label}</td>
            <td>${m.count}</td>
            <td>${formatNum(m.total)} ریال</td>
        </tr>`; }).join('');
    } catch (err) { showToast('خطا در بارگذاری', 'error'); }
}

function exportSales() {
    const from = document.getElementById('rptFromISO')?.value || '';
    const to = document.getElementById('rptToISO')?.value || '';
    const params = new URLSearchParams();
    if (from) params.set('date_from', from);
    if (to) params.set('date_to', to);
    API.exportExcel(params.toString());
}
