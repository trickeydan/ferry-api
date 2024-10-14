from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView

from ferry.core.mixins import BreadcrumbsMixin
from ferry.pub.models import PubEvent, PubEventQuerySet
from ferry.pub.repository import annotate_attendee_count, get_attendees_for_pub_event


class PubEventListView(LoginRequiredMixin, BreadcrumbsMixin, ListView):
    breadcrumbs = [(None, "Pub"), (None, "Events")]
    template_name = "pub/event_list.html"

    def get_queryset(self) -> PubEventQuerySet:
        assert self.request.user.is_authenticated
        qs = PubEvent.objects.for_user(self.request.user)
        qs = qs.order_by("-timestamp")
        qs = annotate_attendee_count(qs)
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        upcoming_pub = PubEvent.objects.get_next()
        return super().get_context_data(
            upcoming_pub=upcoming_pub,
            attendees=get_attendees_for_pub_event(upcoming_pub) if upcoming_pub else None,
            **kwargs,
        )


class PubEventDetailView(LoginRequiredMixin, BreadcrumbsMixin, DetailView):
    template_name = "pub/event_detail.html"

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [
            (None, "Pub"),
            (reverse_lazy("pub:events-list"), "Events"),
            (None, str(self.object)),
        ]

    def get_queryset(self) -> PubEventQuerySet:
        assert self.request.user.is_authenticated
        qs = PubEvent.objects.for_user(self.request.user)
        qs = annotate_attendee_count(qs)
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return super().get_context_data(
            attendees=get_attendees_for_pub_event(self.object),
            **kwargs,
        )
