from typing import Any
from uuid import UUID

from django import http
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousOperation
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, ListView
from django.views.generic.detail import SingleObjectMixin
from rules.contrib.views import PermissionRequiredMixin

from ferry.core.http import HttpRequest
from ferry.core.mixins import BreadcrumbsMixin
from ferry.pub.forms import PubEventRSVPManualEntryForm
from ferry.pub.models import PubEvent, PubEventBooking, PubEventQuerySet, PubEventRSVP, PubEventRSVPMethod
from ferry.pub.repository import annotate_attendee_count, get_attendees_for_pub_event, get_pub_booking_form


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
            upcoming_pub_booking_form=get_pub_booking_form(upcoming_pub) if upcoming_pub else None,
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
            booking_form=get_pub_booking_form(self.object),
            **kwargs,
        )


class AddPubEventBookingView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: UUID) -> http.HttpResponse:
        assert request.user.is_authenticated
        assert request.user.person

        pub_event = get_object_or_404(PubEvent.objects.for_user(request.user), id=pk)

        try:
            _ = pub_event.booking
            messages.error(request, "A booking already exists for that event.")
            return redirect("pub:events-detail", pk=pk)
        except PubEventBooking.DoesNotExist:
            pass

        form = get_pub_booking_form(pub_event, data=request.POST)

        if form.is_valid():
            messages.success(request, "Added booking. Thanks!")
            PubEventBooking.objects.create(
                pub_event=pub_event, created_by=request.user.person, table_size=form.cleaned_data["table_size"]
            )
        else:
            messages.error(request, "Something was wrong with your booking info.")

        return redirect("pub:events-detail", pk=pk)


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
                "booking_form": get_pub_booking_form(pub_event),
            },
        )


class PubEventManualRSVPView(
    LoginRequiredMixin, PermissionRequiredMixin, SingleObjectMixin, BreadcrumbsMixin, FormView
):
    form_class = PubEventRSVPManualEntryForm
    permission_required = "pub.record_attendance"
    template_name = "pub/event_manual_rsvp.html"

    def get_form_kwargs(self) -> dict[str, Any]:
        return {
            **super().get_form_kwargs(),
            "pub_event": self.get_object(),
        }

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        self.object = self.get_object()
        return super().get_context_data(object=self.object)

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [
            (None, "Pub"),
            (reverse_lazy("pub:events-list"), "Events"),
            (reverse_lazy("pub:events-detail", args=[self.object.id]), str(self.object)),
            (None, "Add Manual RSVP"),
        ]

    def get_queryset(self) -> PubEventQuerySet:
        assert self.request.user.is_authenticated
        qs = PubEvent.objects.for_user(self.request.user).select_related("booking")
        qs = annotate_attendee_count(qs)
        return qs

    def form_valid(self, form: PubEventRSVPManualEntryForm) -> http.HttpResponse:
        person = form.cleaned_data["person"]
        PubEventRSVP.objects.create(
            person=person, pub_event=form.pub_event, is_attending=True, method=PubEventRSVPMethod.MANUAL
        )
        messages.success(self.request, f"Marked {person} as present")
        return redirect("pub:events-detail", form.pub_event.id)
