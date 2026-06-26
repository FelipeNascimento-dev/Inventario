from django.shortcuts import redirect
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('', lambda request: redirect('inventario/', permanent=False)),
    path('inventario/', include('inventario.urls')),
    path('inventario/admin/', admin.site.urls),
]