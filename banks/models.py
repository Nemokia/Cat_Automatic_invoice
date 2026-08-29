from django.db import models
from django.conf import settings


class Bank(models.Model):
    """Bank reference table."""
    name = models.CharField(max_length=100, unique=True, verbose_name='نام بانک')
    code = models.CharField(max_length=10, blank=True, verbose_name='کد بانک')
    logo = models.ImageField(upload_to='bank_logos/', blank=True, null=True)

    class Meta:
        verbose_name = 'بانک'
        verbose_name_plural = 'بانک‌ها'
        ordering = ['name']

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    """Bank account linked to a seller user."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bank_accounts')
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT, related_name='accounts', verbose_name='بانک')
    card_number = models.CharField(max_length=16, verbose_name='شماره کارت')
    iban = models.CharField(max_length=30, verbose_name='شماره شبا')
    account_holder = models.CharField(max_length=200, verbose_name='صاحب حساب')
    account_number = models.CharField(max_length=20, blank=True, verbose_name='شماره حساب')
    is_default = models.BooleanField(default=False, verbose_name='پیش‌فرض')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'حساب بانکی'
        verbose_name_plural = 'حساب‌های بانکی'
        ordering = ['-is_default', '-created_at']

    def __str__(self):
        return f'{self.bank.name} - {self.card_number}'

    def save(self, *args, **kwargs):
        if self.is_default:
            BankAccount.objects.filter(
                user=self.user, is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
