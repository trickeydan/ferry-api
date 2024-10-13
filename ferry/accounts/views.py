from __future__ import annotations

from typing import Any
from uuid import UUID

from django import http
from django.contrib import messages
from django.contrib.auth import login, mixins
from django.contrib.auth import views as auth_views
from django.core.exceptions import SuspiciousOperation
from django.db.models.base import Model as Model
from django.db.models.query import QuerySet
from django.forms import BaseModelForm
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, ListView, UpdateView, View

from ferry.accounts.forms import PersonProfileForm, UserPersonLinkForm
from ferry.accounts.models import Person
from ferry.core.http import HttpRequest

from .models import APIToken, User
from .oauth import oauth_config


class LoginView(auth_views.LoginView):
    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> http.HttpResponse:  # type: ignore[override]
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
    def get(self, request: HttpRequest) -> http.HttpResponseRedirect | http.HttpResponseServerError:
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
    success_url = reverse_lazy("court:scoreboard")

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> http.HttpResponseBase:  # type: ignore[override]
        assert request.user.is_authenticated

        if request.user.person is not None:
            return redirect("court:scoreboard")

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form: UserPersonLinkForm) -> http.HttpResponse:
        form.save()
        messages.info(self.request, "Your Discord account has been successfully linked.")
        return super().form_valid(form)


class ProfileView(mixins.LoginRequiredMixin, UpdateView):
    form_class = PersonProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset: QuerySet[Any] | None = None) -> Person:
        assert self.request.user.is_authenticated
        assert self.request.user.person
        return self.request.user.person

    def form_valid(self, form: BaseModelForm) -> http.HttpResponse:
        messages.info(self.request, "Updated profile.")
        return super().form_valid(form)


class ProfileAPITokenView(mixins.LoginRequiredMixin, ListView):
    template_name = "accounts/api_tokens.html"
    success_url = reverse_lazy("accounts:api-tokens")

    def get_queryset(self) -> QuerySet[APIToken]:
        assert self.request.user.is_authenticated
        return self.request.user.api_tokens.all()


class DeactivateAPITokenView(mixins.LoginRequiredMixin, View):
    new_state = False

    def post(self, request: HttpRequest, pk: UUID) -> http.HttpResponse:
        assert request.user.is_authenticated

        if not request.htmx:
            raise SuspiciousOperation("That request is not valid.")

        api_token = get_object_or_404(request.user.api_tokens, id=pk)
        api_token.is_active = self.new_state
        api_token.save()

        return render(request, "accounts/api_tokens__table_row.html", {"api_token": api_token})


class ReactivateAPITokenView(DeactivateAPITokenView):
    new_state = True
