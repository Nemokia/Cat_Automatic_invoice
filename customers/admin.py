from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'phone', 'user']
    list_filter = ['user']
    search_fields = ['first_name', 'last_name', 'phone']
