from django.db import models
from django.conf import settings
from decimal import Decimal


class Product(models.Model):
    """Product model with latest price tracking."""
    FREQUENCY_CHOICES = [
        ('', ''),
        ('hourly', 'ساعتی'),
        ('daily', 'روزانه'),
        ('weekly', 'هفتگی'),
        ('monthly', 'ماهانه'),
        ('yearly', 'سالانه'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200, verbose_name='نام کالا')
    unit = models.CharField(max_length=20, blank=True, default='عدد', verbose_name='واحد')
    frequency = models.CharField(max_length=10, blank=True, default='', choices=FREQUENCY_CHOICES, verbose_name='دوره تکرار')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ['-updated_at']
        unique_together = ['user', 'name']

    def __str__(self):
        return self.name

    @property
    def latest_price(self):
        price = self.price_history.order_by('-date', '-id').first()
        return price.price if price else Decimal('0')

    @property
    def latest_price_date(self):
        price = self.price_history.order_by('-date', '-id').first()
        return price.date if price else None

    @property
    def total_sold(self):
        from django.db.models import Sum
        result = self.invoice_items.aggregate(total=Sum('quantity'))
        return result['total'] or 0

    @property
    def total_revenue(self):
        from django.db.models import Sum
        result = self.invoice_items.aggregate(total=Sum('total_price'))
        return result['total'] or Decimal('0')


class PriceHistory(models.Model):
    """Price history - never overwrites, keeps full history."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    price = models.DecimalField(max_digits=15, decimal_places=0, verbose_name='قیمت')
    date = models.DateField(auto_now_add=True, verbose_name='تاریخ')

    class Meta:
        verbose_name = 'تاریخچه قیمت'
        verbose_name_plural = 'تاریخچه قیمت‌ها'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.product.name} - {self.price}'
