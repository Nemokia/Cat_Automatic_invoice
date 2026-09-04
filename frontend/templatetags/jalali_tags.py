"""Jalali (Shamsi) date template filters — server-side date display."""
from datetime import date, datetime, timezone, timedelta

from django import template
from django.conf import settings
register = template.Library()

JALALI_MONTHS = [
    'فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور',
    'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند',
]

FA_DIGITS = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


def _to_jalali(gy, gm, gd):
    """Gregorian -> Jalali (jalaali-js algorithm)."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = (gm > 2) and (gy + 1) or gy
    days = (355666 + (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100)
            + ((gy2 + 399) // 400) + gd + g_d_m[gm - 1])
    jy = -1595 + (33 * (days // 12053))
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def fa_num(n):
    return str(n).translate(FA_DIGITS)


@register.filter
def jalali(value):
    """Gregorian date -> '۱۴۰۴/۰۵/۱۲'"""
    if not value:
        return '-'
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        return value
    jy, jm, jd = _to_jalali(value.year, value.month, value.day)
    return f'{fa_num(jy)}/{fa_num(f"{jm:02d}")}/{fa_num(f"{jd:02d}")}'


@register.filter
def jalali_datetime(value):
    """Gregorian datetime -> '۱۴۰۴/۰۵/۱۲ — ۱۴:۳۰' (Jalali date + time, in server TIME_ZONE)."""
    if not value:
        return '-'
    if isinstance(value, datetime):
        # Convert to Django's TIME_ZONE if tz-aware
        if value.tzinfo is not None:
            try:
                import zoneinfo
                tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)
            except Exception:
                tz = timezone(timedelta(hours=3, minutes=30))
            value = value.astimezone(tz)
        jy, jm, jd = _to_jalali(value.year, value.month, value.day)
        date_part = f'{fa_num(jy)}/{fa_num(f"{jm:02d}")}/{fa_num(f"{jd:02d}")}'
        time_part = f'{fa_num(f"{value.hour:02d}")}:{fa_num(f"{value.minute:02d}")}'
        return f'{date_part} — {time_part}'
    if isinstance(value, date):
        jy, jm, jd = _to_jalali(value.year, value.month, value.day)
        return f'{fa_num(jy)}/{fa_num(f"{jm:02d}")}/{fa_num(f"{jd:02d}")}'
    return value


@register.filter
def toman(value):
    """Convert rial to toman (÷10) and format with Persian digits + thousand separators."""
    try:
        n = int(value) // 10
        formatted = f'{n:,}'.replace(',', '٬')
        return fa_num(formatted)
    except (ValueError, TypeError):
        return value


@register.filter
def jalali_words(value):
    """Gregorian date -> '۱۲ مرداد ۱۴۰۴'"""
    if not value:
        return '-'
    if isinstance(value, datetime):
        value = value.date()
    if not isinstance(value, date):
        return value
    jy, jm, jd = _to_jalali(value.year, value.month, value.day)
    return f'{fa_num(jd)} {JALALI_MONTHS[jm - 1]} {fa_num(jy)}'


@register.filter
def json_script_safe(value):
    """Serialize value to JSON for embedding in a <script type="application/json"> tag."""
    import json
    from django.utils.safestring import mark_safe

    def _default(o):
        if hasattr(o, 'isoformat'):
            return o.isoformat()
        return str(o)

    return mark_safe(json.dumps(value, default=_default, ensure_ascii=False))
