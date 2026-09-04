from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from .models import Customer
from .serializers import CustomerSerializer, CustomerAutocompleteSerializer
from .matching import find_customer_match, normalize_name, normalize_phone


class CustomerListCreateView(generics.ListCreateAPIView):
    serializer_class = CustomerSerializer

    def get_queryset(self):
        return Customer.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.query_params.get('autocomplete'):
            return CustomerAutocompleteSerializer
        return CustomerSerializer


class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CustomerSerializer

    def get_queryset(self):
        return Customer.objects.filter(user=self.request.user)


@api_view(['GET'])
def customer_autocomplete(request):
    """Fast autocomplete endpoint."""
    q = request.query_params.get('q', '').strip()
    if len(q) < 1:
        return Response([])

    customers = Customer.objects.filter(
        user=request.user
    ).filter(
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q) |
        Q(phone__icontains=q)
    )[:10]

    return Response(CustomerAutocompleteSerializer(customers, many=True).data)


@api_view(['POST'])
def customer_check_match(request):
    """Smart match: given full_name + phone, classify against existing customers.

    Returns {status, primary, candidates} — see customers/matching.py.
    Used by the invoice form to decide between reuse / popup / auto-create.
    """
    full_name = (request.data.get('full_name') or '').strip()
    phone = (request.data.get('phone') or '').strip()
    if not full_name and not phone:
        return Response({'status': 'none', 'primary': None, 'candidates': []})
    result = find_customer_match(request.user, full_name, phone)
    return Response(result)
