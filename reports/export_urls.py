from django.urls import path
from . import export_views

urlpatterns = [
    path('excel/', export_views.export_excel, name='export-excel'),
    path('pdf/<int:customer_id>/', export_views.export_customer_invoices_pdf, name='export-customer-invoices-pdf'),
]
