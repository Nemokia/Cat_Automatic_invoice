from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.BankListView.as_view(), name='bank-list'),
    path('accounts/', views.BankAccountListCreateView.as_view(), name='bankaccount-list'),
    path('accounts/<int:pk>/', views.BankAccountDetailView.as_view(), name='bankaccount-detail'),
]
