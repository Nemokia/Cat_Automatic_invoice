/* ============================================
   Layout JS — Sidebar toggle, More menu, Toasts
   Minimal interaction JS needed on every page.
   ============================================ */

function toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('open');
    document.getElementById('sidebarOverlay')?.classList.toggle('show');
}

function toggleMoreMenu(e) {
    e.preventDefault();
    document.getElementById('moreOverlay')?.classList.add('show');
}

function closeMoreMenu() {
    document.getElementById('moreOverlay')?.classList.remove('show');
}

/* Auto-dismiss Django messages as toasts */
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.toast').forEach(t => {
        setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 300); }, 3500);
    });
});

/* <dialog> confirm-delete helper */
function confirmDelete(formEl, msg) {
    let dlg = document.getElementById('confirmDialog');
    if (!dlg) {
        dlg = document.createElement('dialog');
        dlg.id = 'confirmDialog';
        dlg.innerHTML = `
            <div class="dialog-box">
                <p id="confirmMsg"></p>
                <div class="dialog-actions">
                    <button class="btn btn-danger" id="confirmYes">بله، حذف</button>
                    <button class="btn btn-secondary" id="confirmNo">انصراف</button>
                </div>
            </div>`;
        document.body.appendChild(dlg);
        dlg.querySelector('#confirmNo').onclick = () => dlg.close();
    }
    dlg.querySelector('#confirmMsg').textContent = msg || 'آیا از حذف اطمینان دارید؟';
    dlg.querySelector('#confirmYes').onclick = () => { dlg.close(); formEl.submit(); };
    dlg.showModal();
}

/* Intercept form[data-confirm] submit — opens <dialog> instead of confirm() */
document.addEventListener('submit', function(e) {
    const form = e.target;
    if (form.dataset.confirm) {
        e.preventDefault();
        confirmDelete(form, form.dataset.confirm);
    }
}, true);
