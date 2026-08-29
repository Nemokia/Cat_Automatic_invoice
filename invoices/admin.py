from django.contrib import admin
from .models import Invoice, InvoiceItem, InvoiceNumberSequence

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'customer_name', 'invoice_date', 'final_amount', 'is_paid']
    list_filter = ['is_paid', 'invoice_date']
    search_fields = ['invoice_number', 'customer_name']
    inlines = [InvoiceItemInline]

@admin.register(InvoiceNumberSequence)
class InvoiceNumberSequenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'year', 'last_number']
