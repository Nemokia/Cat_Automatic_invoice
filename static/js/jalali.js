/* ============================================
   Jalali (Solar Hijri / Shamsi) Calendar
   Pure JS conversion between Gregorian and Jalali.
   Backend stores Gregorian dates; this converts
   for display and picking, then back to ISO.
   ============================================ */

const Jalali = {
    // Month names (فروردین..اسفند)
    MONTHS: [
        'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
        'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند'
    ],
    WEEKDAYS: [
        'شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه',
        'چهارشنبه', 'پنجشنبه', 'جمعه'
    ],

    // Gregorian -> Jalali (jalaali-js algorithm)
    toJalali(gy, gm, gd) {
        const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
        let gy2 = (gm > 2) ? (gy + 1) : gy;
        let days = 355666 + (365 * gy) + ~~((gy2 + 3) / 4) - ~~((gy2 + 99) / 100)
                 + ~~((gy2 + 399) / 400) + gd + g_d_m[gm - 1];
        let jy = -1595 + (33 * ~~(days / 12053));
        days %= 12053;
        jy += 4 * ~~(days / 1461);
        days %= 1461;
        if (days > 365) {
            jy += ~~((days - 1) / 365);
            days = (days - 1) % 365;
        }
        let jm, jd;
        if (days < 186) {
            jm = 1 + ~~(days / 31);
            jd = 1 + (days % 31);
        } else {
            jm = 7 + ~~((days - 186) / 30);
            jd = 1 + ((days - 186) % 30);
        }
        return [jy, jm, jd];
    },

    // Jalali -> Gregorian
    toGregorian(jy, jm, jd) {
        const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
        jy += 1595;
        let days = -355668 + 365 * jy + ~~(jy / 33) * 8
                 + ~~(((jy % 33) + 3) / 4) + jd + ((jm < 7) ? (jm - 1) * 31 : ((jm - 7) * 30) + 186);
        let gy = 400 * ~~(days / 146097);
        days %= 146097;
        if (days > 36524) {
            gy += 100 * ~~(--days / 36524);
            days %= 36524;
            if (days >= 365) days++;
        }
        gy += 4 * ~~(days / 1461);
        days %= 1461;
        if (days > 365) {
            gy += ~~((days - 1) / 365);
            days = (days - 1) % 365;
        }
        let gd = days + 1;
        let gm = (gd < 32) ? 1
               : (gd < 61) ? 2
               : (gd < 92) ? 3
               : (gd < 122) ? 4
               : (gd < 152) ? 5
               : (gd < 182) ? 6
               : (gd < 213) ? 7
               : (gd < 244) ? 8
               : (gd < 274) ? 9
               : (gd < 305) ? 10
               : (gd < 335) ? 11 : 12;
        if (gm > 1) gd -= g_d_m[gm - 1];
        return [gy, gm, gd];
    },

    // ISO date string "YYYY-MM-DD" -> {jy, jm, jd}
    fromISO(iso) {
        if (!iso) return null;
        const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
        if (!m) return null;
        const [gy, gm, gd] = [parseInt(m[1]), parseInt(m[2]), parseInt(m[3])];
        const j = this.toJalali(gy, gm, gd);
        return { jy: j[0], jm: j[1], jd: j[2] };
    },

    // {jy,jm,jd} -> ISO "YYYY-MM-DD"
    toISO(j) {
        const g = this.toGregorian(j.jy, j.jm, j.jd);
        return `${g[0]}-${String(g[1]).padStart(2, '0')}-${String(g[2]).padStart(2, '0')}`;
    },

    // Format for display: "۱۴۰۴/۰۵/۱۲"
    format(j, withWords = false) {
        if (!j) return '-';
        const fa = n => String(n).replace(/\d/g, d => '۰۱۲۳۴۵۶۷۸۹'[d]);
        if (withWords) {
            return `${fa(j.jd)} ${this.MONTHS[j.jm - 1]} ${fa(j.jy)}`;
        }
        return `${fa(j.jy)}/${fa(String(j.jm).padStart(2, '0'))}/${fa(String(j.jd).padStart(2, '0'))}`;
    },

    // Days in Jalali month (leap-aware). jy/jm are Jalali year/month numbers.
    daysInMonth(jy, jm) {
        // Standard ~33y cycle: months 1-6=31, 7-11=30, 12=29 or 30 (leap)
        let days;
        if (jm <= 6) days = 31;
        else if (jm <= 11) days = 30;
        else {
            // Leap year when 1 + (jy % 33 * 8 / 33) drops below threshold
            // mathem: leap if ((jy + 1) % 33 * 8 + 4) % 33 < 8 ... use known rule
            days = this.isLeap(jy) ? 30 : 29;
        }
        return days;
    },

    isLeap(jy) {
        // Solar Hijri leap calculation
        return (jy % 33 === 1 || jy % 33 === 5 || jy % 33 === 9 || jy % 33 === 13 ||
                jy % 33 === 17 || jy % 33 === 22 || jy % 33 === 26 ||
                jy % 33 === 30);
    },

    today() {
        const n = new Date();
        return this.fromISO(`${n.getFullYear()}-${String(n.getMonth() + 1).padStart(2, '0')}-${String(n.getDate()).padStart(2, '0')}`);
    },

    // Add months to a jalali date, returns new jalali {jy,jm,jd} clamped to month length
    addMonths(j, n) {
        let jy = j.jy, jm = j.jm + n;
        while (jm > 12) { jm -= 12; jy++; }
        while (jm < 1) { jm += 12; jy--; }
        const maxDay = this.daysInMonth(jy, jm);
        const jd = Math.min(j.jd, maxDay);
        return { jy, jm, jd };
    }
};
