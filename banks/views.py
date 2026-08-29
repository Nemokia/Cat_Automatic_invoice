from rest_framework import generics, status
from rest_framework.response import Response
from .models import Bank, BankAccount
from .serializers import BankSerializer, BankAccountSerializer, BankAccountSelectSerializer


class BankListView(generics.ListAPIView):
    serializer_class = BankSerializer
    queryset = Bank.objects.all()
    pagination_class = None


class BankAccountListCreateView(generics.ListCreateAPIView):
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.request.query_params.get('select'):
            return BankAccountSelectSerializer
        return BankAccountSerializer


class BankAccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        return BankAccount.objects.filter(user=self.request.user)


def seed_banks():
    """Seed initial bank data."""
    banks = [
        'بانک ملی', 'بانک صادرات', 'بانک تجارت', 'بانک ملت',
        'بانک رفاه', 'بانک کشاورزی', 'بانک مسکن', 'بانک سپه',
        'بانک پاسارگاد', 'بانک سامان', 'بانک پارسیان', 'بانک کارآفرین',
        'بانک اقتصاد نوین', 'بانک شهر', 'بانک دی', 'بانک آینده',
        'بانک سرمایه', 'بانک خاورمیانه', 'پست بانک', 'بانک توسعه تعاون',
    ]
    for name in banks:
        Bank.objects.get_or_create(name=name)
