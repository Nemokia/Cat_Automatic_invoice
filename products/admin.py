from django.contrib import admin
from .models import Product, PriceHistory

class PriceHistoryInline(admin.TabularInline):
    model = PriceHistory
    extra = 0

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'user']
    list_filter = ['user']
    search_fields = ['name']
    inlines = [PriceHistoryInline]

@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'price', 'date']
