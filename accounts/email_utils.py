import re
import random
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


# ---- Strict email validation ----

# Blocked disposable/temporary email domains
BLOCKED_DOMAINS = {
    'mailinator.com', 'guerrillamail.com', 'guerrillamail.net', 'guerrillamail.org',
    'tempmail.com', 'temp-mail.org', 'temp-mail.io', 'throwaway.email',
    'yopmail.com', 'yopmail.fr', 'yopmail.net', 'trashmail.com', 'trashmail.net',
    'trashmail.org', 'trashmail.me', 'mailnesia.com', 'maildrop.cc',
    'sharklasers.com', 'guerrillamailblock.com', 'grr.la', 'dispostable.com',
    'mailcatch.com', 'mailnull.com', 'jetable.org', 'nospam.ze.tc',
    'nomail.xl.cx', 'mega.zik.dj', 'speed.1s.fr', 'courriel.fr.nf',
    'moncourrier.fr.nf', 'monemail.fr.nf', 'monmail.fr.nf',
    'fakeinbox.com', 'tempinbox.com', 'mohmal.com', 'burnermail.io',
    'guerrillamail.de', 'guerrillamail.info', 'guerrillamail.biz',
    'gtempmail.com', 'tempr.email', 'discard.email', 'discardmail.com',
    'mailsac.com', 'mailnull.com', 'spamgourmet.com', 'mytemp.email',
    'tmpmail.net', 'tmpmail.org', '10minutemail.com', 'minutemail.com',
    'emailondeck.com', 'harakirimail.com', 'tmail.ws', 'tmpmail.org',
    'getnada.com', 'maildrop.cc', 'inboxalias.com', 'testmail.app',
    'mailsucker.net', 'mailzilla.com', 'trashymail.com', 'trashymail.net',
    'mailexpire.com', 'mailfreeonline.com', 'mailtothis.com',
}

# Valid email regex — strict
EMAIL_REGEX = re.compile(
    r'^(?!.*\.\.)(?!.*\.$)(?!^\.)'                  # no double dots, no leading/trailing dots
    r'[a-zA-Z0-9]'                                   # must start with alphanumeric
    r'[a-zA-Z0-9._%+\-]*'                            # local part
    r'@'
    r'[a-zA-Z0-9]'                                   # domain must start with alphanumeric
    r'[a-zA-Z0-9.\-]*'                               # domain body
    r'\.[a-zA-Z]{2,}$'                               # TLD at least 2 chars
)


def validate_email_strict(email):
    """Validate email with strict rules. Returns (is_valid, error_message)."""
    if not email:
        return False, 'ایمیل الزامی است'

    email = email.strip().lower()

    if not EMAIL_REGEX.match(email):
        return False, 'فرمت ایمیل نامعتبر است'

    # Check blocked domains
    domain = email.split('@')[1]
    if domain in BLOCKED_DOMAINS:
        return False, 'ایمیل‌های موقت پذیرفته نمی‌شوند. لطفاً از ایمیل دائمی استفاده کنید.'

    # Check for common patterns of disposable emails
    local_part = email.split('@')[0]
    if re.match(r'^test\d*$', local_part):
        return False, 'لطفاً از ایمیل واقعی خود استفاده کنید'

    return True, ''


# ---- OTP System ----

def generate_otp():
    """Generate a 5-digit OTP code."""
    return f'{random.randint(10000, 99999)}'


def hash_otp(code):
    """Hash OTP for secure storage."""
    return hashlib.sha256(code.encode()).hexdigest()


def create_otp(user, purpose):
    """Create and store an OTP for the user.

    purpose: 'login' | 'password_change' | 'email_verify'
    Returns the plain code (to be sent via email).
    """
    from .models import OTPCode

    # Delete old unused OTPs for this user+purpose
    OTPCode.objects.filter(user=user, purpose=purpose, is_used=False).delete()

    code = generate_otp()
    OTPCode.objects.create(
        user=user,
        code_hash=hash_otp(code),
        purpose=purpose,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    return code


def verify_otp(user, code, purpose):
    """Verify an OTP code. Returns (is_valid, error_message)."""
    from .models import OTPCode

    if not code or len(code) != 5 or not code.isdigit():
        return False, 'کد تأیید باید ۵ رقم باشد'

    otp = OTPCode.objects.filter(
        user=user,
        purpose=purpose,
        is_used=False,
        expires_at__gt=timezone.now(),
    ).order_by('-created_at').first()

    if not otp:
        return False, 'کد تأیید منقضی شده یا وجود ندارد'

    if otp.attempts >= 5:
        otp.is_used = True
        otp.save()
        return False, 'تعداد تلاش‌ها تمام شد. کد جدید درخواست دهید'

    otp.attempts += 1
    otp.save()

    if otp.code_hash != hash_otp(code):
        remaining = 5 - otp.attempts
        return False, f'کد اشتباه است. {remaining} تلاش باقی مانده'

    # Success
    otp.is_used = True
    otp.save()
    return True, ''


def send_otp_email(user, code, purpose):
    """Send OTP code via email."""
    purpose_labels = {
        'login': 'ورود به حساب کاربری',
        'password_change': 'تغییر رمز عبور',
        'email_verify': 'تأیید ایمیل',
    }
    label = purpose_labels.get(purpose, 'تأیید هویت')

    subject = f'Cat Invoice — کد تأیید {label}'
    message = f'''سلام {user.get_full_name() or user.username}،

کد تأیید شما برای {label}:

    {code}

این کد تا ۵ دقیقه معتبر است.
اگر شما این درخواست را نداده‌اید، این ایمیل را نادیده بگیرید.

با احترام،
تیم Cat Invoice
'''
    try:
        send_mail(
            subject,
            message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@catinvoice.com'),
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f'[OTP] Email send failed: {e}')
        return False
