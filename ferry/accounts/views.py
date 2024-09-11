from __future__ import annotations

from typing import Any

from django import http
from django.contrib import messages
from django.contrib.auth import login, mixins
from django.contrib.auth import views as auth_views
from django.db.models.base import Model as Model
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, View

from ferry.accounts.forms import UserPersonLinkForm

from .models import User
from .oauth import oauth_config


class LoginView(auth_views.LoginView):
    def dispatch(self, request: http.HttpRequest, *args: Any, **kwargs: Any) -> http.HttpResponse:
        # Redirect a user that is already logged in.
        # Borrowed from django.contrib.auth.views.LoginView.dispatch
        if self.request.user.is_authenticated:
            redirect_to = self.get_success_url()
            if redirect_to == self.request.path:
                raise ValueError(
                    "Redirection loop for authenticated user detected. Check that "
                    "your LOGIN_REDIRECT_URL doesn't point to a login page."
                )
            return http.HttpResponseRedirect(redirect_to)

        # Redirect to SSO immediately.
        request.session["sso_next"] = self.get_redirect_url()

        redirect_uri = request.build_absolute_uri(reverse("accounts:sso_oidc_redirect"))
        return oauth_config.sown.authorize_redirect(request, redirect_uri)


class SSOOIDCRedirectView(View):
    def get(self, request: http.HttpRequest) -> http.HttpResponseRedirect | http.HttpResponseServerError:
        token = oauth_config.sown.authorize_access_token(request)
        userinfo = token.get("userinfo", {})

        try:
            username = userinfo["sub"]
        except KeyError:
            return http.HttpResponseServerError("Invalid response from SSO.")

        user, _ = User.objects.get_or_create(username=username)

        self.update_user(user, userinfo)

        login(request, user, backend="django.contrib.auth.backends.ModelBackend")

        from_session = request.session.pop("sso_next", None)

        redirect_to = from_session or "/"
        messages.info(request, f"Signed in via SOWN SSO. Welcome {user.get_short_name()}")
        return redirect(redirect_to)

    def update_user(self, user: User, claims: dict[str, bool | str | list[str]]) -> User:
        full_name = str(claims.get("given_name", ""))

        name_parts = full_name.split(" ")

        if len(name_parts) == 0:
            return user
        elif len(name_parts) == 1:
            user.first_name = name_parts[0]
            user.last_name = ""
        else:
            user.first_name = name_parts.pop(0)
            user.last_name = " ".join(name_parts)

        if email := claims.get("email"):
            user.email = str(email)

        user.save()

        return user


class UnlinkedAccountView(mixins.LoginRequiredMixin, FormView):
    template_name = "accounts/unlinked.html"
    form_class = UserPersonLinkForm
    success_url = reverse_lazy("home")

    def dispatch(self, request: http.HttpRequest, *args: Any, **kwargs: Any) -> http.HttpResponseBase:
        assert request.user.is_authenticated

        if request.user.person is not None:
            return redirect("home")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: UserPersonLinkForm) -> http.HttpResponse:
        form.save()
        messages.info(self.request, "Your Discord account has been successfully linked.")
        return super().form_valid(form)
