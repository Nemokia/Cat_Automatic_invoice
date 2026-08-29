/* ============================================
   Customers Page — Mobile Card Layout
   ============================================ */
async function renderCustomers() {
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header">
        <h1>مشتریان</h1>
        <button class="btn btn-primary" onclick="showCustomerModal()">+ مشتری جدید</button>
      </div>
      <div class="search-bar">
        <input class="form-input" id="custSearch" placeholder="جستجوی مشتری..." oninput="loadCustomers()">
      </div>
      <div id="customerContent">
        <div class="loading-skeleton">
          <div class="skel-row"></div><div class="skel-row"></div><div class="skel-row"></div>
        </div>
      </div>

      <div class="modal-overlay" id="custModal">
        <div class="modal">
          <div class="modal-header">
            <h3 id="custModalTitle">مشتری جدید</h3>
            <button class="modal-close" onclick="closeModal('custModal')">&times;</button>
          </div>
          <div class="modal-body">
            <form id="custForm">
              <div class="invoice-grid">
                <div class="form-group">
                  <label>نام</label>
                  <input class="form-input" id="cfFirst" required>
                </div>
                <div class="form-group">
                  <label>نام خانوادگی</label>
                  <input class="form-input" id="cfLast" required>
                </div>
                <div class="form-group">
                  <label>تلفن</label>
                  <input class="form-input" id="cfPhone">
                </div>
                <div class="form-group">
                  <label>شناسه ملی</label>
                  <input class="form-input" id="cfNatId">
                </div>
                <div class="form-group" style="grid-column:1/-1">
                  <label>آدرس</label>
                  <input class="form-input" id="cfAddr">
                </div>
              </div>
              <input type="hidden" id="cfId">
              <div class="form-actions">
                <button class="btn btn-primary" type="submit">ذخیره</button>
                <button class="btn btn-secondary" type="button" onclick="closeModal('custModal')">لغو</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `);

    loadCustomers();

    document.getElementById('custForm').onsubmit = async (e) => {
        e.preventDefault();
        const id = document.getElementById('cfId').value;
        const data = {
            first_name: document.getElementById('cfFirst').value,
            last_name: document.getElementById('cfLast').value,
            phone: document.getElementById('cfPhone').value,
            national_id: document.getElementById('cfNatId').value,
            address: document.getElementById('cfAddr').value
        };
        try {
            if (id) { await API.updateCustomer(id, data); showToast('مشتری ویرایش شد'); }
            else { await API.createCustomer(data); showToast('مشتری اضافه شد'); }
            closeModal('custModal');
            loadCustomers();
        } catch (err) { showToast(err.message, 'error'); }
    };
}

async function loadCustomers() {
    const q = document.getElementById('custSearch')?.value || '';
    try {
        const data = await API.getCustomers(q);
        const results = data.results || data;
        const container = document.getElementById('customerContent');
        if (!results.length) {
            container.innerHTML = `
              <div class="empty-state">
                <div class="icon">👥</div>
                <p>هنوز مشتری اضافه نشده</p>
                <button class="btn btn-primary" onclick="showCustomerModal()">افزودن مشتری</button>
              </div>`;
            return;
        }
        // Desktop table
        let tableHtml = `
          <div class="table-container desktop-only">
            <table><thead><tr>
              <th>نام</th><th>تلفن</th><th>آدرس</th><th>فاکتورها</th><th>مجموع خرید</th><th>عملیات</th>
            </tr></thead><tbody>
            ${results.map(c => `<tr>
              <td><strong>${escHtml(c.full_name)}</strong></td>
              <td>${escHtml(c.phone || '-')}</td>
              <td>${escHtml(c.address || '-')}</td>
              <td>${c.invoice_count || 0}</td>
              <td><strong>${formatNum(c.total_purchases)} ریال</strong></td>
              <td>
                <button class="btn btn-sm btn-secondary" onclick="editCustomer(${c.id})">ویرایش</button>
                <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${c.id})">حذف</button>
              </td>
            </tr>`).join('')}
            </tbody></table>
          </div>`;

        // Mobile cards
        let cardHtml = `<div class="mobile-cards mobile-only">
          ${results.map(c => `
            <div class="mobile-card">
              <div class="mobile-card-header">
                <strong>${escHtml(c.full_name)}</strong>
              </div>
              <div class="mobile-card-body">
                <div class="mobile-card-row">
                  <span class="card-label">تلفن</span>
                  <span>${escHtml(c.phone || '-')}</span>
                </div>
                <div class="mobile-card-row">
                  <span class="card-label">آدرس</span>
                  <span>${escHtml(c.address || '-')}</span>
                </div>
                <div class="mobile-card-row">
                  <span class="card-label">مجموع خرید</span>
                  <strong>${formatNum(c.total_purchases)} ریال</strong>
                </div>
              </div>
              <div class="mobile-card-actions">
                <button class="btn btn-sm btn-secondary" onclick="editCustomer(${c.id})">ویرایش</button>
                <button class="btn btn-sm btn-danger" onclick="deleteCustomer(${c.id})">حذف</button>
              </div>
            </div>`).join('')}
        </div>`;

        container.innerHTML = tableHtml + cardHtml;
    } catch (err) { showToast('خطا در بارگذاری', 'error'); }
}

function showCustomerModal(cust) {
    document.getElementById('custModalTitle').textContent = cust ? 'ویرایش مشتری' : 'مشتری جدید';
    document.getElementById('cfId').value = cust?.id || '';
    document.getElementById('cfFirst').value = cust?.first_name || '';
    document.getElementById('cfLast').value = cust?.last_name || '';
    document.getElementById('cfPhone').value = cust?.phone || '';
    document.getElementById('cfNatId').value = cust?.national_id || '';
    document.getElementById('cfAddr').value = cust?.address || '';
    openModal('custModal');
}

async function editCustomer(id) {
    try {
        const c = await API.getCustomer(id);
        showCustomerModal(c);
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteCustomer(id) {
    if (!confirm('آیا از حذف این مشتری مطمئنید؟')) return;
    try {
        await API.deleteCustomer(id);
        showToast('مشتری حذف شد');
        loadCustomers();
    } catch (err) { showToast(err.message, 'error'); }
}