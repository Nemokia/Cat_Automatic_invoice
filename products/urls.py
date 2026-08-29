from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProductListCreateView.as_view(), name='product-list'),
    path('autocomplete/', views.product_autocomplete, name='product-autocomplete'),
    path('<int:pk>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<int:product_id>/price/', views.add_price_history, name='add-price'),
]
