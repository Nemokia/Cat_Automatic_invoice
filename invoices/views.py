from rest_framework import generics, filters, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from .models import Invoice
from .serializers import (
    InvoiceListSerializer, InvoiceDetailSerializer, InvoiceCreateSerializer
)


class InvoiceListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return InvoiceCreateSerializer
        return InvoiceListSerializer

    def get_queryset(self):
        qs = Invoice.objects.filter(user=self.request.user)
        # Search
        q = self.request.query_params.get('search', '').strip()
        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q) |
                Q(customer_name__icontains=q) |
                Q(customer_phone__icontains=q) |
                Q(bank_name__icontains=q) |
                Q(card_number__icontains=q) |
                Q(iban__icontains=q) |
                Q(notes__icontains=q) |
                Q(items__product_name__icontains=q)
            ).distinct()
        # Date filters
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(invoice_date__gte=date_from)
        if date_to:
            qs = qs.filter(invoice_date__lte=date_to)
        # Customer filter
        customer_id = self.request.query_params.get('customer_id')
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        return qs


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceDetailSerializer

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)


@api_view(['POST'])
def invoice_duplicate(request, pk):
    """Duplicate an existing invoice."""
    try:
        original = Invoice.objects.get(id=pk, user=request.user)
    except Invoice.DoesNotExist:
        return Response({'detail': 'فاکتور یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

    from .models import InvoiceNumberSequence
    new_data = {
        'user': request.user,
        'invoice_number': InvoiceNumberSequence.get_next_number(request.user),
        'customer': original.customer,
        'customer_name': original.customer_name,
        'customer_phone': original.customer_phone,
        'customer_address': original.customer_address,
        'seller_name': original.seller_name,
        'seller_business': original.seller_business,
        'seller_address': original.seller_address,
        'seller_phone': original.seller_phone,
        'invoice_date': original.invoice_date,
        'due_date': original.due_date,
        'invoice_tax_rate': original.invoice_tax_rate,
        'discount_type': original.discount_type,
        'discount_value': original.discount_value,
        'bank_name': original.bank_name,
        'card_number': original.card_number,
        'iban': original.iban,
        'account_holder': original.account_holder,
        'notes': original.notes,
    }
    new_invoice = Invoice.objects.create(**new_data)

    for item in original.items.all():
        item.pk = None
        item.invoice = new_invoice
        item.save()

    new_invoice.calculate_totals()
    new_invoice.save()

    return Response(InvoiceDetailSerializer(new_invoice).data, status=status.HTTP_201_CREATED)
