from django.contrib import admin
from .models import Bank, BankAccount

@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ['bank', 'card_number', 'account_holder', 'user']
    list_filter = ['bank']
