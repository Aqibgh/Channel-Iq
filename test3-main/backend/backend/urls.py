# backend/urls.py 
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.views.generic import TemplateView
from django.middleware.csrf import get_token
from django.conf import settings
import os

# A simple view for the root URL
def index(request):
    return HttpResponse("Welcome to Django!")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'),
    path('api/', include('app.urls')),
]

# Serve media files during development
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
