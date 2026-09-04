from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom user model for multi-tenant architecture."""
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'کاربر'
        verbose_name_plural = 'کاربران'

    def __str__(self):
        return self.get_full_name() or self.username


class OTPCode(models.Model):
    """One-Time Password for login, password change, email verification."""
    PURPOSE_CHOICES = [
        ('login', 'ورود'),
        ('password_change', 'تغییر رمز'),
        ('email_verify', 'تأیید ایمیل'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_codes')
    code_hash = models.CharField(max_length=64, verbose_name='هش کد')
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, verbose_name='منظور')
    attempts = models.IntegerField(default=0, verbose_name='تعداد تلاش')
    is_used = models.BooleanField(default=False, verbose_name='استفاده شده')
    expires_at = models.DateTimeField(verbose_name='انقضا')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'کد یکبارمصرف'
        verbose_name_plural = 'کدهای یکبارمصرف'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.purpose}'

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class SellerProfile(models.Model):
    """Seller profile linked to a user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=200, blank=True, verbose_name='نام کسب‌وکار')
    national_id = models.CharField(max_length=20, blank=True, verbose_name='شناسه ملی')
    address = models.TextField(blank=True, verbose_name='آدرس')
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name='لوگو')
    custom_units = models.JSONField(default=list, blank=True, verbose_name='واحدهای سفارشی')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'پروفایل فروشنده'
        verbose_name_plural = 'پروفایل‌های فروشنده'

    def __str__(self):
        return self.business_name or self.user.get_full_name()
