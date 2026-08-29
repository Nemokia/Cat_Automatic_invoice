from django.db import models, transaction
from django.conf import settings
from decimal import Decimal
import datetime


class InvoiceNumberSequence(models.Model):
    """Tracks invoice number sequences per user per year."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    year = models.IntegerField()
    last_number = models.IntegerField(default=0)

    class Meta:
        unique_together = ['user', 'year']

    @classmethod
    def get_next_number(cls, user):
        year = datetime.date.today().year
        with transaction.atomic():
            seq, created = cls.objects.select_for_update().get_or_create(
                user=user, year=year, defaults={'last_number': 0}
            )
            seq.last_number += 1
            seq.save()
            return f'INV-{year}-{seq.last_number:06d}'


class Invoice(models.Model):
    """Invoice with snapshot data for historical accuracy."""
    DISCOUNT_PERCENT = 'percent'
    DISCOUNT_AMOUNT = 'amount'
    DISCOUNT_CHOICES = [
        (DISCOUNT_PERCENT, 'درصد'),
        (DISCOUNT_AMOUNT, 'مبلغ'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=30, unique=True, verbose_name='شماره فاکتور')

    # Snapshot: customer info at time of invoice
    customer_name = models.CharField(max_length=200, blank=True, verbose_name='نام مشتری')
    customer_phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن مشتری')
    customer_address = models.TextField(blank=True, verbose_name='آدرس مشتری')
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoices', verbose_name='مشتری'
    )

    # Snapshot: seller info
    seller_name = models.CharField(max_length=200, blank=True, verbose_name='نام فروشنده')
    seller_business = models.CharField(max_length=200, blank=True, verbose_name='نام کسب‌وکار')
    seller_address = models.TextField(blank=True, verbose_name='آدرس فروشنده')
    seller_phone = models.CharField(max_length=15, blank=True, verbose_name='تلفن فروشنده')

    # Dates
    invoice_date = models.DateField(verbose_name='تاریخ فاکتور')
    due_date = models.DateField(null=True, blank=True, verbose_name='تاریخ سررسید')

    # Financial
    subtotal = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='جمع')
    item_taxes_total = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='جمع مالیات اقلام')
    invoice_tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ مالیات فاکتور')
    invoice_tax_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='مالیات فاکتور')
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_CHOICES, blank=True, verbose_name='نوع تخفیف')
    discount_value = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='مقدار تخفیف')
    discount_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='مبلغ تخفیف')
    final_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='مبلغ نهایی')

    # Bank snapshot
    bank_name = models.CharField(max_length=100, blank=True, verbose_name='نام بانک')
    card_number = models.CharField(max_length=20, blank=True, verbose_name='شماره کارت')
    iban = models.CharField(max_length=30, blank=True, verbose_name='شماره شبا')
    account_holder = models.CharField(max_length=200, blank=True, verbose_name='صاحب حساب')

    # Notes & signatures
    notes = models.TextField(blank=True, verbose_name='توضیحات')
    seller_signature = models.ImageField(upload_to='signatures/', blank=True, null=True, verbose_name='امضای فروشنده')
    customer_signature = models.ImageField(upload_to='signatures/', blank=True, null=True, verbose_name='امضای مشتری')

    # Status
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'فاکتور'
        verbose_name_plural = 'فاکتورها'
        ordering = ['-invoice_date', '-created_at']

    def __str__(self):
        return f'{self.invoice_number} - {self.customer_name}'

    def calculate_totals(self):
        """Recalculate all financial totals from items."""
        items = self.items.all()
        self.subtotal = sum(item.total_price for item in items)
        self.item_taxes_total = sum(item.tax_amount for item in items)

        taxable = self.subtotal
        if self.invoice_tax_rate > 0:
            self.invoice_tax_amount = (taxable * self.invoice_tax_rate / Decimal('100')).quantize(Decimal('1'))
        else:
            self.invoice_tax_amount = Decimal('0')

        if self.discount_type == self.DISCOUNT_PERCENT and self.discount_value > 0:
            self.discount_amount = (taxable * self.discount_value / Decimal('100')).quantize(Decimal('1'))
        elif self.discount_type == self.DISCOUNT_AMOUNT:
            self.discount_amount = self.discount_value
        else:
            self.discount_amount = Decimal('0')

        self.final_amount = (
            self.subtotal + self.item_taxes_total + self.invoice_tax_amount - self.discount_amount
        )
        if self.final_amount < 0:
            self.final_amount = Decimal('0')
        return self.final_amount


class InvoiceItem(models.Model):
    """Invoice line item with snapshot pricing."""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(
        'products.Product', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='invoice_items'
    )

    # Snapshot: product info at time of invoice
    product_name = models.CharField(max_length=200, verbose_name='نام کالا')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name='تعداد')
    unit_price = models.DecimalField(max_digits=15, decimal_places=0, verbose_name='قیمت واحد')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='نرخ مالیات')
    total_price = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='مبلغ کل')
    tax_amount = models.DecimalField(max_digits=15, decimal_places=0, default=0, verbose_name='مالیات')
    unit = models.CharField(max_length=20, blank=True, default='عدد', verbose_name='واحد')

    order = models.PositiveIntegerField(default=0, verbose_name='ردیف')

    class Meta:
        verbose_name = 'قلم فاکتور'
        verbose_name_plural = 'اقلام فاکتور'
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.product_name} x {self.quantity}'

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        if self.tax_rate > 0:
            self.tax_amount = (self.total_price * self.tax_rate / Decimal('100')).quantize(Decimal('1'))
        else:
            self.tax_amount = Decimal('0')
        super().save(*args, **kwargs)
