/* ============================================
   Products Page
   ============================================ */
async function renderProducts() {
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header">
        <h1>محصولات</h1>
        <button class="btn btn-primary" onclick="showProductModal()">+ محصول جدید</button>
      </div>
      <div class="search-bar">
        <input class="form-input" id="prodSearch" placeholder="جستجوی محصول..." oninput="loadProducts()">
      </div>
      <div class="table-container">
        <table><thead><tr>
          <th>نام</th><th>واحد</th><th>قیمت فعلی</th><th>فروش</th><th>درآمد</th><th>عملیات</th>
        </tr></thead><tbody id="prodBody"></tbody></table>
      </div>

      <div class="modal-overlay" id="prodModal">
        <div class="modal">
          <div class="modal-header">
            <h3 id="prodModalTitle">محصول جدید</h3>
            <button class="modal-close" onclick="closeModal('prodModal')">&times;</button>
          </div>
          <div class="modal-body">
            <form id="prodForm">
              <div class="invoice-grid">
                <div class="form-group">
                  <label>نام کالا</label>
                  <input class="form-input" id="pfName" required>
                </div>
                <div class="form-group">
                  <label>واحد</label>
                  <select class="form-select" id="pfUnit" onchange="toggleFrequency()">
                    <option value="عدد">عدد</option>
                    <option value="کیلوگرم">کیلوگرم</option>
                    <option value="متر">متر</option>
                    <option value="لیتر">لیتر</option>
                    <option value="بسته">بسته</option>
                    <option value="جعبه">جعبه</option>
                    <option value="خدمات">خدمات</option>
                  </select>
                </div>
                <div class="form-group" id="pfFreqGroup" style="display:none;">
                  <label>دوره تکرار</label>
                  <select class="form-select" id="pfFreq">
                    <option value="hourly">ساعتی</option>
                    <option value="daily">روزانه</option>
                    <option value="weekly">هفتگی</option>
                    <option value="monthly">ماهانه</option>
                    <option value="yearly">سالانه</option>
                  </select>
                </div>
                <div class="form-group" style="grid-column:1/-1">
                  <label>توضیحات</label>
                  <input class="form-input" id="pfDesc">
                </div>
                <div class="form-group">
                  <label>قیمت (ریال)</label>
                  <input class="form-input" id="pfPrice" type="number" min="0">
                </div>
              </div>
              <input type="hidden" id="pfId">
              <div style="margin-top:16px;display:flex;gap:10px;">
                <button class="btn btn-primary" type="submit">ذخیره</button>
                <button class="btn btn-secondary" type="button" onclick="closeModal('prodModal')">لغو</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `);

    loadProducts();

    document.getElementById('prodForm').onsubmit = async (e) => {
        e.preventDefault();
        const id = document.getElementById('pfId').value;
        const data = {
            name: document.getElementById('pfName').value,
            unit: document.getElementById('pfUnit').value,
            frequency: document.getElementById('pfUnit').value === 'خدمات' ? document.getElementById('pfFreq').value : '',
            description: document.getElementById('pfDesc').value
        };
        try {
            let product;
            if (id) {
                await API.updateProduct(id, data);
                product = { id };
                showToast('محصول ویرایش شد');
            } else {
                product = await API.createProduct(data);
                showToast('محصول اضافه شد');
            }
            // Add price history if price provided
            const price = document.getElementById('pfPrice').value;
            if (price && product?.id) {
                await API.addPrice(product.id, { price: parseInt(price) });
            }
            closeModal('prodModal');
            loadProducts();
        } catch (err) { showToast(err.message, 'error'); }
    };
}

async function loadProducts() {
    const q = document.getElementById('prodSearch')?.value || '';
    try {
        const data = await API.getProducts(q);
        const results = data.results || data;
        const tbody = document.getElementById('prodBody');
        if (!results.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">محصولی یافت نشد</td></tr>';
            return;
        }
        tbody.innerHTML = results.map(p => `<tr>
            <td><strong>${escHtml(p.name)}</strong></td>
            <td>${escHtml(p.unit || '-')}${p.unit === 'خدمات' && p.frequency ? ' <small style="color:var(--text-muted)">(' + escHtml(FREQ_LABELS[p.frequency] || p.frequency) + ')</small>' : ''}</td>
            <td>${formatNum(p.latest_price)} ریال</td>
            <td>${p.total_sold || 0}</td>
            <td>${formatNum(p.total_revenue)} ریال</td>
            <td>
              <button class="btn btn-sm btn-secondary" onclick="editProduct(${p.id})">ویرایش</button>
              <button class="btn btn-sm btn-danger" onclick="deleteProduct(${p.id})">حذف</button>
            </td>
        </tr>`).join('');
    } catch (err) { showToast('خطا در بارگذاری', 'error'); }
}

function showProductModal(prod) {
    document.getElementById('prodModalTitle').textContent = prod ? 'ویرایش محصول' : 'محصول جدید';
    document.getElementById('pfId').value = prod?.id || '';
    document.getElementById('pfName').value = prod?.name || '';
    document.getElementById('pfUnit').value = prod?.unit || 'عدد';
    document.getElementById('pfFreq').value = prod?.frequency || 'daily';
    toggleFrequency();
    document.getElementById('pfDesc').value = prod?.description || '';
    document.getElementById('pfPrice').value = prod?.latest_price || '';
    openModal('prodModal');
}

async function editProduct(id) {
    try {
        const p = await API.getProduct(id);
        showProductModal(p);
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteProduct(id) {
    if (!confirm('آیا از حذف این محصول مطمئنید؟')) return;
    try {
        await API.deleteProduct(id);
        showToast('محصول حذف شد');
        loadProducts();
    } catch (err) { showToast(err.message, 'error'); }
}

const FREQ_LABELS = { hourly: 'ساعتی', daily: 'روزانه', weekly: 'هفتگی', monthly: 'ماهانه', yearly: 'سالانه' };

function toggleFrequency() {
    const isService = document.getElementById('pfUnit')?.value === 'خدمات';
    const grp = document.getElementById('pfFreqGroup');
    if (grp) grp.style.display = isService ? '' : 'none';
}
