from django.urls import path
from . import views

urlpatterns = [
    path('', views.CustomerListCreateView.as_view(), name='customer-list'),
    path('autocomplete/', views.customer_autocomplete, name='customer-autocomplete'),
    path('<int:pk>/', views.CustomerDetailView.as_view(), name='customer-detail'),
]
