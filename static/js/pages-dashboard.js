/* ============================================
   Dashboard Page
   ============================================ */
async function renderDashboard() {
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header"><h1>داشبورد</h1></div>
      <div class="stats-grid" id="statsGrid">
        <div class="stat-card"><div class="label">فاکتورها</div><div class="value" id="s1">...</div></div>
        <div class="stat-card accent"><div class="label">درآمد کل</div><div class="value" id="s2">...</div></div>
        <div class="stat-card green"><div class="label">محصولات</div><div class="value" id="s3">...</div></div>
        <div class="stat-card"><div class="label">مشتریان</div><div class="value" id="s4">...</div></div>
      </div>
      <div class="card">
        <div class="card-header"><h3>آخرین فاکتورها</h3></div>
        <div class="table-container">
          <table><thead><tr>
            <th>شماره</th><th>مشتری</th><th>تاریخ</th><th>مبلغ</th>
          </tr></thead><tbody id="recentBody"></tbody></table>
        </div>
      </div>
    `);

    try {
        const d = await API.getDashboard();
        document.getElementById('s1').textContent = formatNum(d.total_invoices);
        document.getElementById('s2').textContent = formatNum(d.total_revenue) + ' ریال';
        document.getElementById('s3').textContent = formatNum(d.total_products);
        document.getElementById('s4').textContent = formatNum(d.total_customers);

        const tbody = document.getElementById('recentBody');
        if (d.recent_invoices && d.recent_invoices.length) {
            tbody.innerHTML = d.recent_invoices.map(inv => `<tr>
                <td>${escHtml(inv.invoice_number)}</td>
                <td>${escHtml(inv.customer_name || '-')}</td>
                <td>${formatDate(inv.invoice_date)}</td>
                <td>${formatNum(inv.final_amount)} ریال</td>
            </tr>`).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:20px;color:#888;">هنوز فاکتوری ثبت نشده</td></tr>';
        }
    } catch (err) {
        showToast('خطا در بارگذاری داشبورد', 'error');
    }
}
