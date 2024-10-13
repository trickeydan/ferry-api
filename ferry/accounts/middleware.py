from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import resolve

from ferry.core.http import HttpRequest


class UserLinkedToPersonMiddleware:
    EXCLUDED_PATHS: set[tuple[str | None, str]] = {
        ("accounts", "logout"),
        ("accounts", "sso_oidc_redirect"),
        ("accounts", "unlinked_account"),
        (None, "api-v2-docs"),
        (None, "api-v2-schema"),
    }

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated and request.user.person is None:
            if self._request_requires_linked_person(request):
                return redirect("accounts:unlinked_account")
        return self.get_response(request)

    def _request_requires_linked_person(self, request: HttpRequest) -> bool:
        path_info = resolve(request.path_info)

        if path_info.app_name in ("admin", "api-2.0.0"):
            return False

        # Django Debug Toolbar
        if settings.DEBUG and path_info.app_name == "djdt":  # pragma: nocover
            return False

        path = (path_info.app_name or None, path_info.url_name)
        return path not in self.EXCLUDED_PATHS
