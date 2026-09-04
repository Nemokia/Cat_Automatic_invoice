from django.urls import path
from . import views

urlpatterns = [
    path('', views.CustomerListCreateView.as_view(), name='customer-list'),
    path('autocomplete/', views.customer_autocomplete, name='customer-autocomplete'),
    path('check-match/', views.customer_check_match, name='customer-check-match'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
]
