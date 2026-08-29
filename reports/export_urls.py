from django.urls import path
from . import export_views

urlpatterns = [
    path('excel/', export_views.export_excel, name='export-excel'),
]
