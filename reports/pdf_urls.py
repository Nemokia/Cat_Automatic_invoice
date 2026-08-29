from django.urls import path
from . import pdf_views

urlpatterns = [
    path('<int:invoice_id>/', pdf_views.generate_pdf, name='invoice-pdf'),
]
