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
]
