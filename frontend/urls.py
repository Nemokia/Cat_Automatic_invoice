from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Auth
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard_view, name='dashboard'),

    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/new/', views.InvoiceCreateView.as_view(), name='invoice_create'),
    path('invoices/<int:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.InvoiceEditView.as_view(), name='invoice_edit'),
    path('invoices/<int:pk>/print/', views.invoice_print_view, name='invoice_print'),
    path('invoices/<int:pk>/pdf/', views.invoice_pdf_view, name='invoice_pdf'),
    path('invoices/<int:pk>/duplicate/', views.invoice_duplicate_view, name='invoice_duplicate'),
    path('invoices/<int:pk>/delete/', views.invoice_delete_view, name='invoice_delete'),
    path('invoices/bulk-delete/', views.invoice_bulk_delete_view, name='invoice_bulk_delete'),

    # Customers
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/new/', views.CustomerCreateView.as_view(), name='customer_create'),
    path('customers/<int:pk>/edit/', views.CustomerEditView.as_view(), name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete_view, name='customer_delete'),
    path('customers/bulk-delete/', views.customer_bulk_delete_view, name='customer_bulk_delete'),

    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/new/', views.ProductCreateView.as_view(), name='product_create'),
    path('products/<int:pk>/edit/', views.ProductEditView.as_view(), name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete_view, name='product_delete'),
    path('products/bulk-delete/', views.product_bulk_delete_view, name='product_bulk_delete'),

    # Banks
    path('banks/', views.BankListView.as_view(), name='bank_list'),
    path('banks/new/', views.BankCreateView.as_view(), name='bank_create'),
    path('banks/<int:pk>/edit/', views.BankEditView.as_view(), name='bank_edit'),
    path('banks/<int:pk>/delete/', views.bank_delete_view, name='bank_delete'),
    path('banks/bulk-delete/', views.bank_bulk_delete_view, name='bank_bulk_delete'),

    # Reports (tab via ?type=sales|customers|products)
    path('reports/', views.reports_view, name='report_sales'),
    path('reports/export/', views.reports_export_view, name='report_export_excel'),
    path('reports/export/pdf/<int:customer_id>/', views.reports_export_customer_pdf_view, name='report_export_customer_pdf'),

    # Settings
    path('settings/', views.settings_view, name='settings'),

    # Autocomplete (JSON endpoints for JS — session-auth, not JWT)
    path('search/customers/', views.customer_autocomplete_view, name='customer_autocomplete'),
    path('search/customers/check-similar/', views.customer_check_similar, name='customer_check_similar'),
    path('search/products/', views.product_autocomplete_view, name='product_autocomplete'),
    path('search/bank-accounts/', views.bank_account_autocomplete_view, name='bank_account_autocomplete'),
    # Custom units
    path('units/', views.units_list_view, name='units_list'),
    path('units/add/', views.unit_add_view, name='unit_add'),
    path('units/delete/', views.unit_delete_view, name='unit_delete'),
]
