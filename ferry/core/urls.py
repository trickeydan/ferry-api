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
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from ferry.core.api.router import urls as api_urls

urlpatterns = []

urlpatterns = [
    path("", include("ferry.dashboard.urls", namespace="dashboard")),
    path("accounts/", include("ferry.accounts.urls")),
    path("ferries/", include("ferry.court.urls", namespace="court")),
    path("admin/", admin.site.urls),
    path("api/", TemplateView.as_view(template_name="api_index.html")),
    # API v2
    path("api/v2/schema/", SpectacularAPIView.as_view(), name="api-v2-schema"),
    path("api/v2/docs/", SpectacularSwaggerView.as_view(url_name="api-v2-schema"), name="api-v2-docs"),
    path("api/v2/", include((api_urls, "api-2.0.0"), namespace="api")),
]

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
