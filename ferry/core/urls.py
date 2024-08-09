"""
URL configuration for ferry project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path
from django.views.generic import TemplateView

from ferry.api_legacy.api import urls as api_urls

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html")),
    path("admin/", admin.site.urls),
    path("api/", TemplateView.as_view(template_name="api_index.html")),
    path("api/docs/", TemplateView.as_view(template_name="api_index.html")),
    path("api/v1/", api_urls),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
