from django.shortcuts import redirect
from django.contrib import admin
from django.urls import path, include

from inventario.views.health_view import health_check

urlpatterns = [
    path('health/', health_check, name='health'),
    path('', lambda request: redirect('inventario/', permanent=False)),
    path('inventario/', include('inventario.urls')),
    path('inventario/admin/', admin.site.urls),
]