from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
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

    def create(self, request, *args, **kwargs):
        # Idempotency: check X-Idempotency-Key header
        idempotency_key = request.headers.get('X-Idempotency-Key')
        if idempotency_key:
            existing = Invoice.objects.filter(
                user=request.user,
                idempotency_key=idempotency_key
            ).first()
            if existing:
                return Response(
                    InvoiceDetailSerializer(existing).data,
                    status=status.HTTP_200_OK
                )

        response = super().create(request, *args, **kwargs)

        # Store idempotency key on the created invoice
        if idempotency_key and response.status_code == 201:
            invoice_id = response.data.get('id')
            if invoice_id:
                Invoice.objects.filter(id=invoice_id).update(
                    idempotency_key=idempotency_key
                )

        return response


class InvoiceDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        # PATCH/PUT use the create serializer: it carries the smart-customer
        # and manual bank fields; GET keeps the rich detail serializer.
        if self.request.method in ('PUT', 'PATCH'):
            return InvoiceCreateSerializer
        return InvoiceDetailSerializer

    def get_queryset(self):
        return Invoice.objects.filter(user=self.request.user)

    def update(self, request, *args, **kwargs):
        # Conflict detection: check If-Unmodified-Since or version
        invoice = self.get_object()
        client_version = request.headers.get('X-Client-Version')
        if client_version:
            try:
                client_ver = int(client_version)
                if client_ver < invoice.version:
                    return Response(
                        {
                            'conflict': True,
                            'server_version': invoice.version,
                            'server_data': InvoiceDetailSerializer(invoice).data,
                            'message': 'این فاکتور توسط کاربر دیگری یا در دستگاه دیگر تغییر کرده است.',
                        },
                        status=status.HTTP_409_CONFLICT
                    )
            except (ValueError, TypeError):
                pass

        response = super().update(request, *args, **kwargs)

        # Increment version after successful update
        if response.status_code in (200, 204):
            invoice.refresh_from_db()
            invoice.version = (invoice.version or 0) + 1
            invoice.save(update_fields=['version'])

        return response


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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_batch_view(request):
    """Batch sync endpoint for offline operations.

    Accepts a list of operations and processes them atomically.
    Each operation has: { type, url, method, payload, clientId }
    Returns results per operation with conflict detection.
    """
    operations = request.data.get('operations', [])
    if not operations:
        return Response({'detail': 'هیچ عملیاتی ارسال نشد'}, status=400)

    results = []
    for op in operations:
        client_id = op.get('clientId')
        op_type = op.get('type', '')
        payload = op.get('payload', {})

        # Check idempotency
        if client_id:
            existing = Invoice.objects.filter(
                user=request.user,
                idempotency_key=client_id
            ).first()
            if existing:
                results.append({
                    'clientId': client_id,
                    'success': True,
                    'serverId': existing.pk,
                    'duplicate': True,
                })
                continue

        try:
            if op_type == 'create_invoice':
                from .serializers import InvoiceCreateSerializer
                serializer = InvoiceCreateSerializer(
                    data=payload,
                    context={'request': request}
                )
                if serializer.is_valid():
                    invoice = serializer.save(user=request.user)
                    if client_id:
                        invoice.idempotency_key = client_id
                        invoice.save(update_fields=['idempotency_key'])
                    results.append({
                        'clientId': client_id,
                        'success': True,
                        'serverId': invoice.pk,
                    })
                else:
                    results.append({
                        'clientId': client_id,
                        'success': False,
                        'error': str(serializer.errors),
                    })
            elif op_type == 'update_invoice':
                invoice_id = payload.pop('id', None) or op.get('serverId')
                try:
                    invoice = Invoice.objects.get(id=invoice_id, user=request.user)
                    # Conflict check
                    client_version = op.get('version')
                    if client_version and client_version < invoice.version:
                        results.append({
                            'clientId': client_id,
                            'success': False,
                            'conflict': True,
                            'serverVersion': invoice.version,
                            'serverData': InvoiceDetailSerializer(invoice).data,
                        })
                        continue

                    serializer = InvoiceCreateSerializer(
                        invoice, data=payload, partial=True,
                        context={'request': request}
                    )
                    if serializer.is_valid():
                        invoice = serializer.save()
                        invoice.version = (invoice.version or 0) + 1
                        invoice.save(update_fields=['version'])
                        results.append({
                            'clientId': client_id,
                            'success': True,
                            'serverId': invoice.pk,
                        })
                    else:
                        results.append({
                            'clientId': client_id,
                            'success': False,
                            'error': str(serializer.errors),
                        })
                except Invoice.DoesNotExist:
                    results.append({
                        'clientId': client_id,
                        'success': False,
                        'error': 'فاکتور یافت نشد',
                    })
            else:
                results.append({
                    'clientId': client_id,
                    'success': False,
                    'error': f'نوع عملیات ناشناخته: {op_type}',
                })
        except Exception as e:
            results.append({
                'clientId': client_id,
                'success': False,
                'error': str(e),
            })

    return Response({'results': results})
