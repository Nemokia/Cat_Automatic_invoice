from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse
from rest_framework_simplejwt.views import TokenRefreshView


def service_worker_view(request):
    """Serve sw.js from root for proper scope."""
    sw_path = settings.STATICFILES_DIRS[0] / 'sw.js'
    return FileResponse(open(sw_path, 'rb'), content_type='application/javascript')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('sw.js', service_worker_view, name='service-worker'),
    path('captcha/', include('captcha.urls')),
    # API
    path('api/auth/', include('accounts.urls')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('api/customers/', include('customers.urls')),
    path('api/products/', include('products.urls')),
    path('api/invoices/', include('invoices.urls')),
    path('api/banks/', include('banks.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/export/', include('reports.export_urls')),
    path('api/pdf/', include('reports.pdf_urls')),
    # Frontend
    path('', include('frontend.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
