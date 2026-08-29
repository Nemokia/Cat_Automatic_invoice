/* ============================================
   Settings Page (Profile, Seller, Password)
   ============================================ */
async function renderSettings() {
    const user = API.getUser();
    const app = document.getElementById('app');
    app.innerHTML = buildLayout(`
      <div class="page-header"><h1>تنظیمات</h1></div>
      <div class="tabs">
        <button class="tab-btn active" onclick="showSettingsTab('profile',this)">پروفایل</button>
        <button class="tab-btn" onclick="showSettingsTab('seller',this)">کسب‌وکار</button>
        <button class="tab-btn" onclick="showSettingsTab('password',this)">تغییر رمز</button>
      </div>

      <div id="settingsTab">
        <div class="card" id="profileTab">
          <h3 style="margin-bottom:16px;">اطلاعات شخصی</h3>
          <form id="profileForm">
            <div class="invoice-grid">
              <div class="form-group">
                <label>نام</label>
                <input class="form-input" id="pfFirst" value="${escHtml(user?.first_name || '')}">
              </div>
              <div class="form-group">
                <label>نام خانوادگی</label>
                <input class="form-input" id="pfLast" value="${escHtml(user?.last_name || '')}">
              </div>
              <div class="form-group">
                <label>ایمیل</label>
                <input class="form-input" id="pfEmail" type="email" value="${escHtml(user?.email || '')}">
              </div>
              <div class="form-group">
                <label>تلفن</label>
                <input class="form-input" id="pfPhone" value="${escHtml(user?.phone || '')}">
              </div>
            </div>
            <button class="btn btn-primary" type="submit">ذخیره</button>
          </form>
        </div>
      </div>
    `);

    // Load seller profile
    try {
        const sp = await API.getSellerProfile();
        window._sellerProfile = sp;
    } catch (e) { window._sellerProfile = {}; }

    document.getElementById('profileForm').onsubmit = async (e) => {
        e.preventDefault();
        try {
            await API.updateProfile({
                first_name: document.getElementById('pfFirst').value,
                last_name: document.getElementById('pfLast').value,
                email: document.getElementById('pfEmail').value,
                phone: document.getElementById('pfPhone').value
            });
            showToast('پروفایل ذخیره شد');
            const u = await API.getProfile();
            API.setUser(u);
        } catch (err) { showToast(err.message, 'error'); }
    };
}

function showSettingsTab(tab, btn) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const container = document.getElementById('settingsTab');
    const sp = window._sellerProfile || {};

    if (tab === 'profile') {
        container.innerHTML = document.getElementById('profileTab')?.outerHTML || '';
        // Re-attach handler
    } else if (tab === 'seller') {
        container.innerHTML = `
        <div class="card">
          <h3 style="margin-bottom:16px;">اطلاعات کسب‌وکار</h3>
          <form id="sellerForm">
            <div class="invoice-grid">
              <div class="form-group">
                <label>نام کسب‌وکار</label>
                <input class="form-input" id="sfBiz" value="${escHtml(sp.business_name || '')}">
              </div>
              <div class="form-group">
                <label>شناسه ملی</label>
                <input class="form-input" id="sfNatId" value="${escHtml(sp.national_id || '')}">
              </div>
              <div class="form-group">
                <label>تلفن</label>
                <input class="form-input" id="sfPhone" value="${escHtml(sp.phone || '')}">
              </div>
              <div class="form-group">
                <label>ایمیل</label>
                <input class="form-input" id="sfEmail" value="${escHtml(sp.email || '')}">
              </div>
              <div class="form-group" style="grid-column:1/-1">
                <label>آدرس</label>
                <input class="form-input" id="sfAddr" value="${escHtml(sp.address || '')}">
              </div>
            </div>
            <button class="btn btn-primary" type="submit">ذخیره</button>
          </form>
        </div>`;
        document.getElementById('sellerForm').onsubmit = async (e) => {
            e.preventDefault();
            try {
                await API.updateSellerProfile({
                    business_name: document.getElementById('sfBiz').value,
                    national_id: document.getElementById('sfNatId').value,
                    phone: document.getElementById('sfPhone').value,
                    email: document.getElementById('sfEmail').value,
                    address: document.getElementById('sfAddr').value
                });
                showToast('اطلاعات کسب‌وکار ذخیره شد');
            } catch (err) { showToast(err.message, 'error'); }
        };
    } else if (tab === 'password') {
        container.innerHTML = `
        <div class="card">
          <h3 style="margin-bottom:16px;">تغییر رمز عبور</h3>
          <form id="pwForm" style="max-width:400px;">
            <div class="form-group">
              <label>رمز عبور فعلی</label>
              <input class="form-input" id="pwOld" type="password" required>
            </div>
            <div class="form-group">
              <label>رمز عبور جدید</label>
              <input class="form-input" id="pwNew" type="password" required minlength="6">
            </div>
            <div class="form-group">
              <label>تکرار رمز جدید</label>
              <input class="form-input" id="pwNew2" type="password" required minlength="6">
            </div>
            <button class="btn btn-primary" type="submit">تغییر رمز</button>
          </form>
        </div>`;
        document.getElementById('pwForm').onsubmit = async (e) => {
            e.preventDefault();
            const n = document.getElementById('pwNew').value;
            if (n !== document.getElementById('pwNew2').value) {
                showToast('رمزهای جدید مطابقت ندارند', 'error');
                return;
            }
            try {
                await API.changePassword({ old_password: document.getElementById('pwOld').value, new_password: n });
                showToast('رمز عبور تغییر کرد');
                document.getElementById('pwForm').reset();
            } catch (err) { showToast(err.message, 'error'); }
        };
    }
}
