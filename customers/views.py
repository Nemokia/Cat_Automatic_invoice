from rest_framework import generics, filters
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db.models import Q
from .models import Customer
from .serializers import CustomerSerializer, CustomerAutocompleteSerializer


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
