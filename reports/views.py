from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Sum, Count, F, Q
from invoices.models import Invoice, InvoiceItem
from products.models import Product
from customers.models import Customer
from datetime import date, timedelta


@api_view(['GET'])
def sales_report(request):
    """Sales summary report."""
    user = request.user
    invoices = Invoice.objects.filter(user=user)

    date_from = request.query_params.get('date_from')
    date_to = request.query_params.get('date_to')
    if date_from:
        invoices = invoices.filter(invoice_date__gte=date_from)
    if date_to:
        invoices = invoices.filter(invoice_date__lte=date_to)

    stats = invoices.aggregate(
        total_sales=Sum('final_amount'),
        total_tax=Sum('item_taxes_total') or 0,
        total_invoice_tax=Sum('invoice_tax_amount') or 0,
        total_discount=Sum('discount_amount') or 0,
        invoice_count=Count('id'),
    )

    monthly = invoices.values('invoice_date__month', 'invoice_date__year').annotate(
        total=Sum('final_amount'),
        count=Count('id')
    ).order_by('-invoice_date__year', '-invoice_date__month')[:12]

    return Response({
        'summary': stats,
        'monthly': list(monthly),
    })


@api_view(['GET'])
def customer_report(request):
    """Customer analytics."""
    user = request.user
    customers = Customer.objects.filter(user=user).annotate(
        total_spent=Sum('invoices__final_amount'),
        num_invoices=Count('invoices')
    ).order_by('-total_spent')

    return Response([{
        'id': c.id,
        'name': c.full_name,
        'phone': c.phone,
        'total_spent': c.total_spent or 0,
        'num_invoices': c.num_invoices,
    } for c in customers[:50]])


@api_view(['GET'])
def product_report(request):
    """Product analytics."""
    user = request.user
    products = Product.objects.filter(user=user).annotate(
        times_sold=Count('invoice_items'),
        total_revenue=Sum('invoice_items__total_price'),
    ).order_by('-total_revenue')

    return Response([{
        'id': p.id,
        'name': p.name,
        'latest_price': p.latest_price,
        'times_sold': p.times_sold or 0,
        'total_revenue': p.total_revenue or 0,
    } for p in products[:50]])
