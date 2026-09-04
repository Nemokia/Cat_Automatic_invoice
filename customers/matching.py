"""Smart customer matching for the invoice form.

Statuses returned by find_customer_match():
- exact          : same normalized name AND same normalized phone -> reuse customer
- phone_conflict : same phone, different name -> ask user (update name or create new)
- name_conflict  : same name, different phone -> ask user (update phone or create new)
- similar        : fuzzy name overlap (e.g. "زهرا اسلامی" vs "زهرا اسلامیان") -> ask user
- none           : no candidate -> create silently on save/print

The backend never mutates an existing customer without the user's explicit
choice; mutation is done by the frontend calling PATCH after the user picks
"same customer".
"""
import re
import unicodedata

from .models import Customer
from .serializers import CustomerAutocompleteSerializer

_PERSIAN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
_ARABIC_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')


def _latin_digits(s):
    return str(s).translate(_PERSIAN_DIGITS).translate(_ARABIC_DIGITS)


def normalize_phone(raw):
    """Keep digits only; tolerate 98- prefix and missing leading zero."""
    if not raw:
        return ''
    digits = re.sub(r'\D', '', _latin_digits(raw))
    if len(digits) == 12 and digits.startswith('98'):
        digits = '0' + digits[2:]
    if len(digits) == 10 and digits.startswith('9'):
        digits = '0' + digits
    return digits


def normalize_name(raw):
    """Trim, collapse whitespace, unify Arabic chars, casefold."""
    s = _latin_digits(raw or '')
    s = s.replace('ي', 'ی').replace('ك', 'ک')
    s = unicodedata.normalize('NFKC', s)
    return ' '.join(s.split()).casefold()


def parse_full_name(full_name):
    """Split "زهرا اسلامیان" into first/last name for Customer creation."""
    parts = str(full_name or '').strip().split()
    if not parts:
        return '', ''
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])


def _name_tokens(s):
    return [t for t in normalize_name(s).split() if len(t) >= 3]


def _names_similar(a, b):
    """Token-level prefix containment: 'اسلامی' ~ 'اسلامیان'."""
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    for x in ta:
        for y in tb:
            if x.startswith(y) or y.startswith(x):
                return True
    return False


def _serialize(c, reason):
    data = CustomerAutocompleteSerializer(c).data
    data['reason'] = reason
    return dict(data)


def find_customer_match(user, full_name, phone):
    nname = normalize_name(full_name)
    nphone = normalize_phone(phone)

    by_phone, by_name, fuzzy = {}, {}, {}

    for c in Customer.objects.filter(user=user):
        if nphone and normalize_phone(c.phone) == nphone:
            by_phone[c.id] = c
        if nname and normalize_name(c.full_name) == nname:
            by_name[c.id] = c
        elif nname and _names_similar(full_name, c.full_name):
            fuzzy[c.id] = c

    both_ids = [cid for cid in by_phone if cid in by_name]

    candidates, primary, status = [], None, 'none'
    for cid in sorted(both_ids):
        candidates.append(_serialize(by_phone[cid], 'both'))
    for cid in sorted(by_phone):
        if cid not in both_ids:
            candidates.append(_serialize(by_phone[cid], 'phone'))
    for cid in sorted(by_name):
        if cid not in both_ids:
            candidates.append(_serialize(by_name[cid], 'name'))
    for cid in sorted(fuzzy):
        candidates.append(_serialize(fuzzy[cid], 'similar'))

    if both_ids:
        status, primary = 'exact', by_phone[both_ids[0]]
    elif by_phone:
        status, primary = 'phone_conflict', by_phone[sorted(by_phone)[0]]
    elif by_name:
        status, primary = 'name_conflict', by_name[sorted(by_name)[0]]
    elif fuzzy:
        status, primary = 'similar', fuzzy[sorted(fuzzy)[0]]

    return {
        'status': status,
        'primary': CustomerAutocompleteSerializer(primary).data if primary else None,
        'candidates': candidates,
    }
