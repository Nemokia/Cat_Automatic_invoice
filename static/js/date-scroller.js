/* ============================================
   Jalali Date Scroller (wheel picker)
   Reads/writes ISO date behind the scenes,
   displays Jalali text in the visible input.
   openDateScroller(displayInputId, hiddenInputId)
   ============================================ */

function createDateScroller() {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.id = 'dateScrollerModal';
    overlay.innerHTML = `
      <div class="modal" style="max-width:420px;">
        <div class="modal-header">
          <h3>انتخاب تاریخ</h3>
          <button class="modal-close" onclick="closeDateScroller()">&times;</button>
        </div>
        <div class="modal-body">
          <div class="ds-display" id="dsPreview"></div>
          <div class="ds-columns">
            <div class="ds-col" id="dsYearCol">
              <div class="ds-col-label">سال</div>
              <div class="ds-scroll" id="dsYearScroll"></div>
            </div>
            <div class="ds-col" id="dsMonthCol">
              <div class="ds-col-label">ماه</div>
              <div class="ds-scroll" id="dsMonthScroll"></div>
            </div>
            <div class="ds-col" id="dsDayCol">
              <div class="ds-col-label">روز</div>
              <div class="ds-scroll" id="dsDayScroll"></div>
            </div>
          </div>
          <div style="display:flex;gap:10px;margin-top:16px;">
            <button class="btn btn-primary" style="flex:1;" onclick="confirmDateScroller()">تأیید</button>
            <button class="btn btn-secondary" style="flex:1;" onclick="closeDateScroller()">لغو</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(overlay);
}

function faNum(n) {
    return String(n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
}

function openDateScroller(displayId, hiddenId) {
    if (!document.getElementById('dateScrollerModal')) createDateScroller();
    const modal = document.getElementById('dateScrollerModal');
    modal.classList.add('show');
    modal._displayId = displayId;
    modal._hiddenId = hiddenId;

    // Read current ISO from hidden field
    let j;
    const hidden = hiddenId ? document.getElementById(hiddenId) : null;
    if (hidden && hidden.value) {
        j = Jalali.fromISO(hidden.value);
    }
    if (!j) j = Jalali.today();

    const curYear = j.jy;
    const years = [];
    for (let y = curYear - 10; y <= curYear + 10; y++) years.push(y);
    const months = [];
    for (let m = 1; m <= 12; m++) months.push(m);

    buildScrollerColumn('dsYearScroll', years, y => faNum(y), curYear, v => {
        modal._jy = v;
        updateDays();
        updatePreview();
    });
    buildScrollerColumn('dsMonthScroll', months, m => Jalali.MONTHS[m - 1], j.jm, v => {
        modal._jm = v;
        updateDays();
        updatePreview();
    });

    modal._jy = j.jy;
    modal._jm = j.jm;
    updateDays(j.jd);
    updatePreview();
}

function updateDays(selectedDay) {
    const modal = document.getElementById('dateScrollerModal');
    const daysInMonth = Jalali.daysInMonth(modal._jy, modal._jm);
    const days = [];
    for (let d = 1; d <= daysInMonth; d++) days.push(d);
    const currentSel = modal._jd || selectedDay || 1;
    modal._jd = Math.min(currentSel, daysInMonth);
    buildScrollerColumn('dsDayScroll', days, d => faNum(d), modal._jd, v => {
        modal._jd = v;
        updatePreview();
    });
}

function updatePreview() {
    const modal = document.getElementById('dateScrollerModal');
    const j = { jy: modal._jy, jm: modal._jm, jd: modal._jd };
    document.getElementById('dsPreview').textContent = Jalali.format(j, true);
}

function buildScrollerColumn(containerId, items, labelFn, selectedValue, onChange) {
    const container = document.getElementById(containerId);
    const SCROLL_H = 160;
    const ITEM_H = 40;
    const selectedIdx = items.indexOf(selectedValue);

    let html = `<div class="ds-spacer"></div>`;
    items.forEach((item, i) => {
        html += `<div class="ds-item ${i === selectedIdx ? 'ds-selected' : ''}"
                      data-val="${item}" data-idx="${i}">${labelFn(item)}</div>`;
    });
    html += `<div class="ds-spacer"></div>`;
    container.innerHTML = html;
    container.style.height = SCROLL_H + 'px';
    container.style.overflow = 'auto';
    container.style.scrollSnapType = 'y mandatory';
    container.style.webkitOverflowScrolling = 'touch';

    const scrollTo = selectedIdx * ITEM_H;
    container.scrollTop = scrollTo;

    let scrollTimer;
    container.addEventListener('scroll', () => {
        clearTimeout(scrollTimer);
        scrollTimer = setTimeout(() => {
            const idx = Math.round(container.scrollTop / ITEM_H);
            const clamped = Math.max(0, Math.min(idx, items.length - 1));
            const target = clamped * ITEM_H;
            if (Math.abs(container.scrollTop - target) > 1) {
                container.scrollTo({ top: target, behavior: 'smooth' });
            }
            container.querySelectorAll('.ds-item').forEach((el, i) => {
                el.classList.toggle('ds-selected', i === clamped);
            });
            onChange(items[clamped]);
        }, 80);
    }, { passive: true });
}

function confirmDateScroller() {
    const modal = document.getElementById('dateScrollerModal');
    const iso = Jalali.toISO({ jy: modal._jy, jm: modal._jm, jd: modal._jd });
    const jalaliText = Jalali.format({ jy: modal._jy, jm: modal._jm, jd: modal._jd });

    // Set hidden ISO field
    if (modal._hiddenId) {
        const hidden = document.getElementById(modal._hiddenId);
        if (hidden) hidden.value = iso;
    }
    // Set visible Jalali text
    const display = document.getElementById(modal._displayId);
    if (display) display.value = jalaliText;

    modal.classList.remove('show');
}

function closeDateScroller() {
    document.getElementById('dateScrollerModal')?.classList.remove('show');
}
