from typing import Any
from uuid import UUID

from django import http
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from ferry.core.http import HttpRequest
from ferry.core.mixins import BreadcrumbsMixin
from ferry.pub.models import PubEvent, PubEventBooking, PubEventQuerySet, PubEventRSVP, PubEventRSVPMethod
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
        assert self.request.user.is_authenticated
        assert self.request.user.person

        upcoming_pub = PubEvent.objects.get_next()
        if upcoming_pub:
            upcoming_pub_rsvp = PubEventRSVP.objects.filter(
                pub_event=upcoming_pub, person=self.request.user.person
            ).first()

            try:
                booking: PubEventBooking | None = upcoming_pub.booking
            except PubEventBooking.DoesNotExist:
                booking = None
        else:
            upcoming_pub_rsvp = None
            booking = None

        return super().get_context_data(
            upcoming_pub=upcoming_pub,
            upcoming_pub_rsvp=upcoming_pub_rsvp,
            upcoming_pub_booking=booking,
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
        qs = PubEvent.objects.for_user(self.request.user).select_related("booking")
        qs = annotate_attendee_count(qs)
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        assert self.request.user.is_authenticated
        assert self.request.user.person

        try:  # TODO: Dedupe
            booking: PubEventBooking | None = self.object.booking
        except PubEventBooking.DoesNotExist:
            booking = None

        rsvp = PubEventRSVP.objects.filter(pub_event=self.object, person=self.request.user.person).first()
        return super().get_context_data(
            attendees=get_attendees_for_pub_event(self.object),
            rsvp=rsvp,
            booking=booking,
            is_past=timezone.now().date() > self.object.timestamp.date(),
            **kwargs,
        )


class UpdatePubEventResponseView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: UUID) -> http.HttpResponse:
        assert request.user.is_authenticated
        assert request.user.person

        if not request.htmx:
            raise SuspiciousOperation("That request is not valid.")

        pub_event = get_object_or_404(PubEvent.objects.for_user(request.user), id=pk)
        rsvp = PubEventRSVP.objects.filter(
            pub_event=pub_event,
            person=request.user.person,
        ).first()

        if not pub_event.is_past:
            if rsvp:
                if rsvp.method == PubEventRSVPMethod.AUTO:
                    with transaction.atomic():
                        rsvp.delete()
                        rsvp = PubEventRSVP(
                            pub_event=pub_event,
                            person=request.user.person,
                            is_attending=False,
                            method=PubEventRSVPMethod.WEB,
                        )
                        rsvp.save()
                elif rsvp.method == PubEventRSVPMethod.DISCORD:
                    # No action
                    pass
                elif rsvp.method == PubEventRSVPMethod.WEB:
                    rsvp.is_attending = not rsvp.is_attending
                    rsvp.save()
                else:
                    # This should be unreachable
                    pass
            else:
                rsvp = PubEventRSVP(
                    pub_event=pub_event,
                    person=request.user.person,
                    is_attending=True,
                    method=PubEventRSVPMethod.WEB,
                )
                rsvp.save()

        try:  # TODO: Dedupe
            booking: PubEventBooking | None = pub_event.booking
        except PubEventBooking.DoesNotExist:
            booking = None

        return render(
            request,
            "pub/inc/event_details.html",
            {
                "event": pub_event,
                "rsvp": rsvp,
                "booking": booking,
                "attendees": get_attendees_for_pub_event(pub_event),
            },
        )
