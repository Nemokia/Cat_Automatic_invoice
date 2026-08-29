/* ============================================
   Bank Accounts Page
   ============================================ */
async function renderBanks() {
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header">
        <h1>حساب‌های بانکی</h1>
        <button class="btn btn-primary" onclick="showBankModal()">+ حساب جدید</button>
      </div>
      <div class="table-container">
        <table><thead><tr>
          <th>بانک</th><th>شماره کارت</th><th>شماره شبا</th><th>صاحب حساب</th><th>پیش‌فرض</th><th>عملیات</th>
        </tr></thead><tbody id="bankBody"></tbody></table>
      </div>

      <div class="modal-overlay" id="bankModal">
        <div class="modal" style="max-width:600px;">
          <div class="modal-header">
            <h3 id="bankModalTitle">حساب بانکی جدید</h3>
            <button class="modal-close" onclick="closeModal('bankModal')">&times;</button>
          </div>
          <div class="modal-body">
            <form id="bankForm">
              <div class="form-group">
                <label>بانک</label>
                <select class="form-select" id="bfBank" required></select>
              </div>
              <div class="form-group">
                <label>شماره کارت</label>
                <input class="form-input" id="bfCard" required maxlength="16">
              </div>
              <div class="form-group">
                <label>شماره شبا</label>
                <input class="form-input" id="bfIban" required maxlength="30">
              </div>
              <div class="form-group">
                <label>صاحب حساب</label>
                <input class="form-input" id="bfHolder" required>
              </div>
              <div class="form-group">
                <label>شماره حساب</label>
                <input class="form-input" id="bfAcctNum">
              </div>
              <div class="form-group">
                <label><input type="checkbox" id="bfDefault"> پیش‌فرض</label>
              </div>
              <input type="hidden" id="bfId">
              <div style="margin-top:16px;display:flex;gap:10px;">
                <button class="btn btn-primary" type="submit">ذخیره</button>
                <button class="btn btn-secondary" type="button" onclick="closeModal('bankModal')">لغو</button>
              </div>
            </form>
          </div>
        </div>
      </div>
    `);

    // Load banks into select
    try {
        const banks = await API.getBanks();
        const sel = document.getElementById('bfBank');
        (banks || []).forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id; opt.textContent = b.name;
            sel.appendChild(opt);
        });
    } catch (e) {}

    loadBanks();

    document.getElementById('bankForm').onsubmit = async (e) => {
        e.preventDefault();
        const id = document.getElementById('bfId').value;
        const data = {
            bank: document.getElementById('bfBank').value,
            card_number: document.getElementById('bfCard').value,
            iban: document.getElementById('bfIban').value,
            account_holder: document.getElementById('bfHolder').value,
            account_number: document.getElementById('bfAcctNum').value,
            is_default: document.getElementById('bfDefault').checked
        };
        try {
            if (id) { await API.updateBankAccount(id, data); showToast('حساب ویرایش شد'); }
            else { await API.createBankAccount(data); showToast('حساب اضافه شد'); }
            closeModal('bankModal');
            loadBanks();
        } catch (err) { showToast(err.message, 'error'); }
    };
}

async function loadBanks() {
    try {
        const data = await API.getBankAccounts();
        const results = data.results || data;
        const tbody = document.getElementById('bankBody');
        if (!results.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">حساب بانکی ثبت نشده</td></tr>';
            return;
        }
        tbody.innerHTML = results.map(a => `<tr>
            <td><strong>${escHtml(a.bank_name)}</strong></td>
            <td>${escHtml(a.card_number)}</td>
            <td>${escHtml(a.iban)}</td>
            <td>${escHtml(a.account_holder)}</td>
            <td>${a.is_default ? '<span class="badge badge-success">بله</span>' : '-'}</td>
            <td>
              <button class="btn btn-sm btn-secondary" onclick="editBank(${a.id})">ویرایش</button>
              <button class="btn btn-sm btn-danger" onclick="deleteBank(${a.id})">حذف</button>
            </td>
        </tr>`).join('');
    } catch (err) { showToast('خطا در بارگذاری', 'error'); }
}

function showBankModal(acc) {
    document.getElementById('bankModalTitle').textContent = acc ? 'ویرایش حساب' : 'حساب جدید';
    document.getElementById('bfId').value = acc?.id || '';
    document.getElementById('bfCard').value = acc?.card_number || '';
    document.getElementById('bfIban').value = acc?.iban || '';
    document.getElementById('bfHolder').value = acc?.account_holder || '';
    document.getElementById('bfAcctNum').value = acc?.account_number || '';
    document.getElementById('bfDefault').checked = acc?.is_default || false;
    if (acc?.bank) document.getElementById('bfBank').value = acc.bank;
    openModal('bankModal');
}

async function editBank(id) {
    try {
        const accts = await API.getBankAccounts();
        const a = (accts || []).find(x => x.id === id);
        if (a) showBankModal(a);
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteBank(id) {
    if (!confirm('آیا از حذف این حساب مطمئنید؟')) return;
    try {
        await API.deleteBankAccount(id);
        showToast('حساب حذف شد');
        loadBanks();
    } catch (err) { showToast(err.message, 'error'); }
}
