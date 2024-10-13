from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path(
        "oidc/redirect/",
        views.SSOOIDCRedirectView.as_view(),
        name="sso_oidc_redirect",
    ),
    path("unlinked/", views.UnlinkedAccountView.as_view(), name="unlinked_account"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("profile/api-tokens/", views.ProfileAPITokenView.as_view(), name="api-tokens"),
    path("profile/api-tokens/<uuid:pk>/activate/", views.ReactivateAPITokenView.as_view(), name="api-tokens-activate"),
    path(
        "profile/api-tokens/<uuid:pk>/deactivate/", views.DeactivateAPITokenView.as_view(), name="api-tokens-deactivate"
    ),
]
