from django.contrib.auth.models import AbstractUser
from django.db import models


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


class SellerProfile(models.Model):
    """Seller profile linked to a user."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='seller_profile')
    business_name = models.CharField(max_length=200, blank=True, verbose_name='نام کسب‌وکار')
    national_id = models.CharField(max_length=20, blank=True, verbose_name='شناسه ملی')
    address = models.TextField(blank=True, verbose_name='آدرس')
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    email = models.EmailField(blank=True, verbose_name='ایمیل')
    logo = models.ImageField(upload_to='logos/', blank=True, null=True, verbose_name='لوگو')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'پروفایل فروشنده'
        verbose_name_plural = 'پروفایل‌های فروشنده'

    def __str__(self):
        return self.business_name or self.user.get_full_name()
