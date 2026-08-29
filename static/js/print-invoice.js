/* ============================================
   Professional Invoice Print Layout
   ============================================ */

// --- Persian helpers ---
const _faDigits = n => String(n || 0).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
const _fmtMoney = n => _faDigits(Number(n || 0).toLocaleString('en'));

// --- Build the full HTML string from a plain data object ---
// data: { invoiceId, sellerName, customerName, customerPhone,
//         invoiceDate, dueDate, isPaid,
//         items: [{name, qty, price, tax, unit}],
//         taxRate, discType, discVal,
//         bankName, cardNumber, iban, accountHolder,
//         notes }
function buildPrintHtml(d) {
    const fa = _faDigits;
    const fmt = _fmtMoney;

    // Calculate item totals
    let subtotal = 0, totalTax = 0;
    const rows = (d.items || []).map((it, idx) => {
        const qty = parseFloat(it.quantity) || 0;
        const price = parseInt(it.unit_price) || 0;
        const tax = parseFloat(it.tax_rate) || 0;
        const lineTotal = qty * price;
        const lineTax = tax > 0 ? Math.round(lineTotal * tax / 100) : 0;
        subtotal += lineTotal;
        totalTax += lineTax;
        return { name: it.product_name || it.name || '', qty, price, tax, lineTotal, lineTax };
    });

    const invTaxRate = parseFloat(d.taxRate) || 0;
    const invTax = Math.round(subtotal * invTaxRate / 100);
    let disc = 0;
    if (d.discType === 'percent') disc = Math.round(subtotal * parseInt(d.discVal) / 100);
    else if (d.discType === 'amount') disc = parseInt(d.discVal) || 0;
    const final_ = Math.max(0, subtotal + totalTax + invTax - disc);

    let itemRows = rows.map((r, i) => `
      <tr>
        <td>${i + 1}</td>
        <td>${escHtml(r.name)}</td>
        <td>${fmt(r.qty)}</td>
        <td>${fmt(r.price)}</td>
        <td>${r.tax > 0 ? r.tax + '%' : '-'}</td>
        <td>${fmt(r.lineTax)}</td>
        <td class="amount">${fmt(r.lineTotal)}</td>
      </tr>`).join('');

    const statusBadge = d.isPaid
        ? '<span class="badge-paid">✓ پرداخت شده</span>'
        : '<span class="badge-unpaid">✗ پرداخت نشده</span>';

    return `<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>چاپ فاکتور</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'Segoe UI', Tahoma, Arial, sans-serif; direction: rtl; background: #f5f5f5; padding: 20px; }
  .invoice { max-width: 800px; margin: 0 auto; background: #fff; border: 2px solid #0B1849; border-radius: 4px; overflow: hidden; }
  .inv-header { background: #0B1849; color: #fff; padding: 24px 30px; display: flex; justify-content: space-between; align-items: center; }
  .inv-header h1 { font-size: 28px; color: #E4B028; }
  .inv-header .inv-num { text-align: left; font-size: 14px; color: rgba(255,255,255,0.8); line-height: 1.8; }
  .inv-header .inv-num strong { color: #E4B028; font-size: 16px; }
  .inv-info { display: flex; gap: 2px; background: #e8e8e8; }
  .inv-info-box { flex: 1; padding: 16px 20px; background: #fff; }
  .inv-info-box h3 { font-size: 13px; color: #0B1849; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 2px solid #E4B028; display: inline-block; }
  .inv-info-box p { font-size: 13px; color: #333; line-height: 1.8; }
  .inv-info-box .label { color: #888; font-size: 12px; }
  .inv-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .inv-table thead th { background: #347433; color: #fff; padding: 10px 12px; text-align: center; font-weight: 600; font-size: 12px; }
  .inv-table tbody td { padding: 9px 12px; border-bottom: 1px solid #eee; text-align: center; }
  .inv-table tbody tr:hover { background: #f9fdf9; }
  .inv-table .amount { font-weight: 700; color: #347433; }
  .inv-totals { display: flex; justify-content: flex-end; padding: 16px 20px; background: #f8f8f8; border-top: 2px solid #ddd; }
  .inv-totals-table { width: 300px; }
  .inv-totals-table .row { display: flex; justify-content: space-between; padding: 5px 0; font-size: 13px; }
  .inv-totals-table .row.total { font-size: 17px; font-weight: 700; color: #0B1849; border-top: 2px solid #E4B028; padding-top: 8px; margin-top: 4px; }
  .inv-bank { margin: 0 20px; padding: 12px 16px; background: #EBEDE3; border-radius: 4px; display: flex; gap: 24px; flex-wrap: wrap; font-size: 13px; }
  .inv-bank span { color: #555; }
  .inv-bank strong { color: #0B1849; }
  .inv-notes { padding: 12px 20px; font-size: 12px; color: #666; border-top: 1px solid #eee; margin-top: 12px; }
  .inv-footer { background: #0B1849; color: rgba(255,255,255,0.5); text-align: center; padding: 10px; font-size: 11px; }
  .inv-status-bar { display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; border-bottom: 1px solid #eee; font-size: 13px; color: #555; }
  .badge-paid { background: #e6f4e6; color: #347433; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px; }
  .badge-unpaid { background: #fff3e0; color: #e6a800; padding: 4px 12px; border-radius: 12px; font-weight: 600; font-size: 12px; }
  .no-print-bar { max-width: 800px; margin: 0 auto 12px; text-align: center; }
  .no-print-bar button { padding: 10px 28px; border: none; border-radius: 6px; font-size: 15px; font-weight: 600; cursor: pointer; margin: 0 6px; font-family: inherit; }
  .btn-print { background: #347433; color: #fff; }
  .btn-print:hover { background: #2a6028; }
  .btn-close { background: #ddd; color: #333; }
  .btn-close:hover { background: #ccc; }
  @media print { body { background: #fff; padding: 0; } .no-print-bar { display: none !important; } .invoice { border: none; border-radius: 0; } }
</style>
</head>
<body>
  <div class="no-print-bar">
    <button class="btn-print" onclick="window.print()">🖨️ چاپ</button>
    <button class="btn-close" onclick="window.close()">بستن</button>
  </div>
  <div class="invoice">
    <div class="inv-header">
      <div>
        <h1>فاکتور فروش</h1>
        <div style="font-size:13px;color:rgba(255,255,255,0.7);margin-top:4px;">${escHtml(d.sellerName || '')}</div>
      </div>
      <div class="inv-num">
        <strong>شماره فاکتور</strong><br>
        ${d.invoiceId ? '#' + fa(d.invoiceId) : '— پیش‌نویس —'}
      </div>
    </div>
    <div class="inv-status-bar">
      <div>تاریخ صدور: <strong>${escHtml(d.invoiceDate || '')}</strong></div>
      ${d.dueDate ? '<div>سررسید: <strong>' + escHtml(d.dueDate) + '</strong></div>' : ''}
      <div>${statusBadge}</div>
    </div>
    <div class="inv-info">
      <div class="inv-info-box">
        <h3>فروشنده</h3>
        <p><span class="label">نام:</span> <strong>${escHtml(d.sellerName || '')}</strong></p>
      </div>
      <div class="inv-info-box">
        <h3>خریدار</h3>
        <p>
          <span class="label">نام:</span> <strong>${escHtml(d.customerName) || '-'}</strong><br>
          <span class="label">تلفن:</span> ${escHtml(d.customerPhone) || '-'}
        </p>
      </div>
    </div>
    <table class="inv-table">
      <thead><tr>
        <th style="width:35px;">ردیف</th><th>شرح کالا / خدمات</th>
        <th style="width:60px;">تعداد</th><th style="width:90px;">قیمت واحد</th>
        <th style="width:55px;">مالیات</th><th style="width:75px;">مالیات مبلغ</th>
        <th style="width:90px;">جمع</th>
      </tr></thead>
      <tbody>${itemRows || '<tr><td colspan="7" style="padding:20px;color:#aaa;">اقلامی ثبت نشده</td></tr>'}</tbody>
    </table>
    <div class="inv-totals">
      <div class="inv-totals-table">
        <div class="row"><span>جمع کل:</span><span>${fmt(subtotal)} ریال</span></div>
        <div class="row"><span>مالیات اقلام:</span><span>${fmt(totalTax)} ریال</span></div>
        ${invTaxRate > 0 ? '<div class="row"><span>مالیات فاکتور ('+fa(invTaxRate)+'%):</span><span>'+fmt(invTax)+' ریال</span></div>' : ''}
        ${disc > 0 ? '<div class="row"><span>تخفیف:</span><span>-'+fmt(disc)+' ریال</span></div>' : ''}
        <div class="row total"><span>مبلغ قابل پرداخت:</span><span>${fmt(final_)} ریال</span></div>
      </div>
    </div>
    ${(d.bankName || d.cardNumber) ? `<div class="inv-bank" style="margin-top:12px;">
      ${d.bankName ? '<div><span>بانک:</span> <strong>'+escHtml(d.bankName)+'</strong></div>' : ''}
      ${d.cardNumber ? '<div><span>کارت:</span> <strong>'+escHtml(d.cardNumber)+'</strong></div>' : ''}
      ${d.iban ? '<div><span>شبا:</span> <strong>'+escHtml(d.iban)+'</strong></div>' : ''}
      ${d.accountHolder ? '<div><span>صاحب حساب:</span> <strong>'+escHtml(d.accountHolder)+'</strong></div>' : ''}
    </div>` : ''}
    ${d.notes ? '<div class="inv-notes"><strong>توضیحات:</strong> '+escHtml(d.notes)+'</div>' : ''}
    <div class="inv-footer">Cat Invoice — سیستم مدیریت فاکتور</div>
  </div>
  <script>window.onload = function(){ window.print(); };</script>
</body></html>`;
}

// --- Open a new window and write HTML into it ---
function _openPrintWindow(html) {
    const win = window.open('', '_blank', 'width=900,height=700');
    if (win) {
        win.document.write(html);
        win.document.close();
    } else {
        showToast('پاپ‌آپ بلاک شده. اجازه پاپ‌آپ بدهید.', 'error');
    }
}

// --- Print from the invoice FORM (unsaved / editing) ---
function printInvoice() {
    const user = API.getUser();
    const sellerName = (user?.first_name + ' ' + user?.last_name).trim() || user?.username || '';
    const data = {
        invoiceId: invoiceEditId || null,
        sellerName,
        customerName: document.getElementById('invCustSearch')?.value || '',
        customerPhone: document.getElementById('invCustInfo')?.textContent || '',
        invoiceDate: document.getElementById('invDate')?.textContent || document.getElementById('invDate')?.value || '',
        dueDate: document.getElementById('invDue')?.textContent || document.getElementById('invDue')?.value || '',
        isPaid: document.getElementById('invPaid')?.checked || false,
        items: invoiceItems,
        taxRate: document.getElementById('invTaxRate')?.value || '0',
        discType: document.getElementById('invDiscType')?.value || '',
        discVal: document.getElementById('invDiscVal')?.value || '0',
        bankName: document.getElementById('invBankName')?.value || '',
        cardNumber: document.getElementById('invCard')?.value || '',
        iban: document.getElementById('invIban')?.value || '',
        accountHolder: document.getElementById('invHolder')?.value || '',
        notes: document.getElementById('invNotes')?.value || '',
    };
    _openPrintWindow(buildPrintHtml(data));
}

// --- Print an EXISTING invoice by ID (from the invoice LIST page) ---
async function printInvoiceById(id) {
    try {
        const inv = await API.getInvoice(id);
        const user = API.getUser();
        const sellerName = inv.seller_name || ((user?.first_name + ' ' + user?.last_name).trim()) || user?.username || '';
        const data = {
            invoiceId: inv.id || id,
            sellerName,
            customerName: inv.customer_name || '',
            customerPhone: inv.customer_phone || '',
            invoiceDate: formatDate(inv.invoice_date),
            dueDate: inv.due_date ? formatDate(inv.due_date) : '',
            isPaid: inv.is_paid,
            items: inv.items || [],
            taxRate: inv.invoice_tax_rate || '0',
            discType: inv.discount_type || '',
            discVal: inv.discount_value || '0',
            bankName: inv.bank_name || '',
            cardNumber: inv.card_number || '',
            iban: inv.iban || '',
            accountHolder: inv.account_holder || '',
            notes: inv.notes || '',
        };
        _openPrintWindow(buildPrintHtml(data));
    } catch (err) {
        showToast('خطا در بارگذاری فاکتور: ' + err.message, 'error');
    }
}
