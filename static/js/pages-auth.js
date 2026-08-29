/* ============================================
   Auth Pages: Login & Register
   ============================================ */
function renderLogin() {
    document.getElementById('app').innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="logo">🐱</div>
        <h1>Cat Invoice</h1>
        <p class="subtitle">سیستم مدیریت فاکتور</p>
        <form id="loginForm">
          <div class="form-group">
            <label>نام کاربری</label>
            <input class="form-input" id="loginUser" placeholder="نام کاربری" required>
          </div>
          <div class="form-group">
            <label>رمز عبور</label>
            <input class="form-input" id="loginPass" type="password" placeholder="رمز عبور" required>
          </div>
          <button class="btn btn-primary btn-block btn-lg" type="submit">ورود</button>
        </form>
        <p style="text-align:center;margin-top:16px;font-size:14px;">
          حساب ندارید؟ <a href="#/register" style="color:var(--green);font-weight:600;">ثبت‌نام</a>
        </p>
      </div>
    </div>`;

    document.getElementById('loginForm').onsubmit = async (e) => {
        e.preventDefault();
        try {
            const data = await API.login({
                username: document.getElementById('loginUser').value,
                password: document.getElementById('loginPass').value
            });
            API.setTokens(data.tokens.access, data.tokens.refresh);
            API.setUser(data.user);
            Router.navigate('/');
        } catch (err) { showToast(err.message, 'error'); }
    };
}

function renderRegister() {
    document.getElementById('app').innerHTML = `
    <div class="auth-page">
      <div class="auth-card">
        <div class="logo">🐱</div>
        <h1>ثبت‌نام</h1>
        <p class="subtitle">ایجاد حساب کاربری جدید</p>
        <form id="regForm">
          <div class="form-group">
            <label>نام کاربری</label>
            <input class="form-input" id="regUser" required>
          </div>
          <div class="form-group">
            <label>نام</label>
            <input class="form-input" id="regFirst" required>
          </div>
          <div class="form-group">
            <label>نام خانوادگی</label>
            <input class="form-input" id="regLast" required>
          </div>
          <div class="form-group">
            <label>ایمیل</label>
            <input class="form-input" id="regEmail" type="email">
          </div>
          <div class="form-group">
            <label>تلفن</label>
            <input class="form-input" id="regPhone">
          </div>
          <div class="form-group">
            <label>رمز عبور</label>
            <input class="form-input" id="regPass" type="password" required>
          </div>
          <div class="form-group">
            <label>تکرار رمز عبور</label>
            <input class="form-input" id="regPass2" type="password" required>
          </div>
          <button class="btn btn-primary btn-block btn-lg" type="submit">ثبت‌نام</button>
        </form>
        <p style="text-align:center;margin-top:16px;font-size:14px;">
          قبلاً ثبت‌نام کرده‌اید؟ <a href="#/login" style="color:var(--green);font-weight:600;">ورود</a>
        </p>
      </div>
    </div>`;

    document.getElementById('regForm').onsubmit = async (e) => {
        e.preventDefault();
        try {
            const data = await API.register({
                username: document.getElementById('regUser').value,
                first_name: document.getElementById('regFirst').value,
                last_name: document.getElementById('regLast').value,
                email: document.getElementById('regEmail').value,
                phone: document.getElementById('regPhone').value,
                password: document.getElementById('regPass').value,
                password_confirm: document.getElementById('regPass2').value
            });
            API.setTokens(data.tokens.access, data.tokens.refresh);
            API.setUser(data.user);
            showToast('ثبت‌نام با موفقیت انجام شد');
            Router.navigate('/');
        } catch (err) { showToast(err.message, 'error'); }
    };
}
