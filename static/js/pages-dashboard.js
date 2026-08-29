/* ============================================
   Dashboard Page — Professional Minimal
   ============================================ */
async function renderDashboard() {
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header">
        <h1>داشبورد</h1>
        <button class="btn btn-primary" onclick="Router.navigate('/invoices/new')">+ فاکتور جدید</button>
      </div>
      <div class="stats-grid" id="statsGrid">
        <div class="stat-card">
          <div class="stat-icon">📄</div>
          <div class="stat-body">
            <div class="label">فاکتورها</div>
            <div class="value" id="s1">—</div>
          </div>
        </div>
        <div class="stat-card accent">
          <div class="stat-icon">💰</div>
          <div class="stat-body">
            <div class="label">درآمد کل</div>
            <div class="value" id="s2">—</div>
          </div>
        </div>
        <div class="stat-card green">
          <div class="stat-icon">📦</div>
          <div class="stat-body">
            <div class="label">محصولات</div>
            <div class="value" id="s3">—</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">👥</div>
          <div class="stat-body">
            <div class="label">مشتریان</div>
            <div class="value" id="s4">—</div>
          </div>
        </div>
      </div>
      <div class="card">
        <div class="card-header">
          <h3>آخرین فاکتورها</h3>
          <a href="#/invoices" class="btn btn-sm btn-secondary">مشاهده همه</a>
        </div>
        <div id="recentSection">
          <div class="loading-skeleton">
            <div class="skel-row"></div>
            <div class="skel-row"></div>
            <div class="skel-row"></div>
          </div>
        </div>
      </div>
    `);

    try {
        const d = await API.getDashboard();
        document.getElementById('s1').textContent = formatNum(d.total_invoices);
        document.getElementById('s2').textContent = formatNum(d.total_revenue) + ' ریال';
        document.getElementById('s3').textContent = formatNum(d.total_products);
        document.getElementById('s4').textContent = formatNum(d.total_customers);

        const section = document.getElementById('recentSection');
        if (d.recent_invoices && d.recent_invoices.length) {
            section.innerHTML = `
              <div class="table-container">
                <table><thead><tr>
                  <th>شماره</th><th>مشتری</th><th>تاریخ</th><th>مبلغ</th>
                </tr></thead><tbody>
                ${d.recent_invoices.map(inv => `<tr onclick="Router.navigate('/invoices/${inv.id}')" style="cursor:pointer;">
                    <td><strong>${escHtml(inv.invoice_number)}</strong></td>
                    <td>${escHtml(inv.customer_name || '-')}</td>
                    <td>${formatDate(inv.invoice_date)}</td>
                    <td><strong>${formatNum(inv.final_amount)} ریال</strong></td>
                </tr>`).join('')}
                </tbody></table>
              </div>`;
        } else {
            section.innerHTML = `
              <div class="empty-state">
                <div class="icon">📄</div>
                <p>هنوز فاکتوری ثبت نشده</p>
                <button class="btn btn-primary" onclick="Router.navigate('/invoices/new')">صدور فاکتور جدید</button>
              </div>`;
        }
    } catch (err) {
        showToast('خطا در بارگذاری داشبورد', 'error');
    }
}
