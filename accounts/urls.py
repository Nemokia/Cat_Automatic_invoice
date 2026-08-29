from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('seller-profile/', views.SellerProfileView.as_view(), name='seller-profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('dashboard/', views.dashboard_stats, name='dashboard-stats'),
]
