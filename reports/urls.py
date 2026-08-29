from django.urls import path
from . import views

urlpatterns = [
    path('sales/', views.sales_report, name='sales-report'),
    path('customers/', views.customer_report, name='customer-report'),
    path('products/', views.product_report, name='product-report'),
]
