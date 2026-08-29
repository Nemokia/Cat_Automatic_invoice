from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from .models import Product, PriceHistory
from .serializers import ProductSerializer, ProductAutocompleteSerializer, PriceHistorySerializer


class ProductListCreateView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.query_params.get('autocomplete'):
            return ProductAutocompleteSerializer
        return ProductSerializer


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)


@api_view(['GET'])
def product_autocomplete(request):
    """Fast autocomplete for products."""
    q = request.query_params.get('q', '').strip()
    if len(q) < 1:
        return Response([])

    products = Product.objects.filter(
        user=request.user,
        name__icontains=q
    )[:10]

    return Response(ProductAutocompleteSerializer(products, many=True).data)


@api_view(['POST'])
def add_price_history(request, product_id):
    """Add a new price entry for a product."""
    try:
        product = Product.objects.get(id=product_id, user=request.user)
    except Product.DoesNotExist:
        return Response({'detail': 'محصول یافت نشد'}, status=status.HTTP_404_NOT_FOUND)

    serializer = PriceHistorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save(product=product)
    return Response(serializer.data, status=status.HTTP_201_CREATED)
