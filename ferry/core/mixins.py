from typing import Any

from django.conf import settings
from django.views.generic.base import ContextMixin


class BreadcrumbsMixin(ContextMixin):
    breadcrumbs: list[tuple[str | None, str]] = []

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        """Returns a list of tuples (url, display)."""
        return [(None, settings.APP_NAME)] + self.breadcrumbs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            breadcrumbs=self.get_breadcrumbs(),
            **kwargs,
        )
