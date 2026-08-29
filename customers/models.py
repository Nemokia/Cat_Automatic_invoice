from django.db import models
from django.conf import settings


class Customer(models.Model):
    """Customer model, isolated per user."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customers')
    first_name = models.CharField(max_length=100, verbose_name='نام')
    last_name = models.CharField(max_length=100, verbose_name='نام خانوادگی')
    phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن')
    address = models.TextField(blank=True, verbose_name='آدرس')
    national_id = models.CharField(max_length=20, blank=True, verbose_name='شناسه ملی')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'مشتری'
        verbose_name_plural = 'مشتریان'
        ordering = ['-created_at']
        unique_together = ['user', 'phone', 'first_name', 'last_name']

    def __str__(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def total_purchases(self):
        return self.invoices.aggregate(
            total=models.Sum('final_amount')
        )['total'] or 0

    @property
    def invoice_count(self):
        return self.invoices.count()
