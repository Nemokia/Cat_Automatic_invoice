from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .serializers import (
    UserRegistrationSerializer, UserSerializer,
    SellerProfileSerializer, ChangePasswordSerializer
)
from .models import SellerProfile

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user).data,
            'tokens': {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        }, status=status.HTTP_201_CREATED)


class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class SellerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = SellerProfileSerializer

    def get_object(self):
        profile, _ = SellerProfile.objects.get_or_create(user=self.request.user)
        return profile


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response({'detail': 'رمز عبور با موفقیت تغییر کرد'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    from django.contrib.auth import authenticate
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is None:
        return Response(
            {'detail': 'نام کاربری یا رمز عبور اشتباه است'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    refresh = RefreshToken.for_user(user)
    return Response({
        'user': UserSerializer(user).data,
        'tokens': {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    })


@api_view(['GET'])
def dashboard_stats(request):
    """Main dashboard statistics."""
    user = request.user
    from invoices.models import Invoice
    from products.models import Product
    from customers.models import Customer

    invoices = Invoice.objects.filter(user=user)
    return Response({
        'total_invoices': invoices.count(),
        'total_revenue': sum(inv.final_amount for inv in invoices),
        'total_products': Product.objects.filter(user=user).count(),
        'total_customers': Customer.objects.filter(user=user).count(),
        'recent_invoices': invoices.values(
            'id', 'invoice_number', 'customer_name', 'invoice_date', 'final_amount'
        )[:5],
    })
