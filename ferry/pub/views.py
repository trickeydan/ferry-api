from typing import Any
from uuid import UUID

from django import http
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from rules.contrib.views import PermissionRequiredMixin

from ferry.accounts.models import Person
from ferry.core.http import HttpRequest
from ferry.core.mixins import BreadcrumbsMixin
from ferry.pub.forms import PubEventRSVPManualEntryForm, PubForm
from ferry.pub.models import (
    Pub,
    PubEvent,
    PubEventAttendanceTombstone,
    PubEventBooking,
    PubEventQuerySet,
    PubEventRSVP,
    PubEventRSVPMethod,
)
from ferry.pub.repository import (
    annotate_attendee_count,
    get_attendees_for_pub_event,
    get_listed_pubs,
    get_next_pub_summary,
    get_pub_booking_form,
)
from ferry.pub.services import TombstoneAlreadyExistsError, set_autopub, skip_next_pub, undo_skip_next_pub


class PubEventListView(LoginRequiredMixin, BreadcrumbsMixin, ListView):
    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [(reverse("pub:overview"), "Pub"), (None, "Events")]

    template_name = "pub/event_list.html"
    paginate_by = 20

    def get_queryset(self) -> PubEventQuerySet:
        assert self.request.user.is_authenticated
        qs = PubEvent.objects.for_user(self.request.user)
        qs = qs.order_by("-timestamp")
        qs = annotate_attendee_count(qs)
        return qs


class PubOverviewView(LoginRequiredMixin, BreadcrumbsMixin, TemplateView):
    breadcrumbs = [(None, "Pub")]
    template_name = "pub/overview.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        assert self.request.user.is_authenticated

        recent_events = PubEvent.objects.for_user(self.request.user).filter(timestamp__lt=timezone.now())
        recent_events = annotate_attendee_count(recent_events.order_by("-timestamp"))[:5]

        return super().get_context_data(
            recent_events=recent_events,
            pubs=get_listed_pubs(self.request.user)[:5],
            **get_next_pub_summary(self.request.user.person),
            **kwargs,
        )


class PubEventDetailView(LoginRequiredMixin, BreadcrumbsMixin, DetailView):
    template_name = "pub/event_detail.html"

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [
            (reverse("pub:overview"), "Pub"),
            (reverse("pub:events-list"), "Events"),
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
                elif rsvp.method == PubEventRSVPMethod.TOMBSTONE:
                    # Coming after skipping is an explicit yes, so the skip no longer applies.
                    with transaction.atomic():
                        PubEventAttendanceTombstone.objects.filter(
                            pub_event=pub_event, person=request.user.person
                        ).delete()
                        rsvp.method = PubEventRSVPMethod.WEB
                        rsvp.is_attending = True
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
            (reverse("pub:overview"), "Pub"),
            (reverse("pub:events-list"), "Events"),
            (reverse("pub:events-detail", args=[self.object.id]), str(self.object)),
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


class AutoPubFragmentsMixin(LoginRequiredMixin):
    """Shared by the htmx views that change AutoPub or skip state.

    The next-pub card and the AutoPub card both depend on that state, so each response swaps in
    the card that was clicked and updates the other one out-of-band when it is on the page.
    """

    def post_checks(self, request: HttpRequest) -> Person:
        assert request.user.is_authenticated
        assert request.user.person

        if not request.htmx:
            raise SuspiciousOperation("That request is not valid.")

        return request.user.person

    def render_fragments(self, request: HttpRequest, person: Person, *, target: str) -> http.HttpResponse:
        on_overview = request.htmx.current_url_abs_path == reverse("pub:overview")
        return render(
            request,
            "pub/inc/autopub_fragments.html",
            {
                **get_next_pub_summary(person),
                "oob_next_card": target != "next",
                "show_autopub_card": target == "autopub" or on_overview,
                "oob_autopub_card": target != "autopub",
            },
        )


class SkipNextPubView(AutoPubFragmentsMixin, View):
    def post(self, request: HttpRequest) -> http.HttpResponse:
        person = self.post_checks(request)

        if not person.autopub:
            raise PermissionDenied("Only people using AutoPub can skip a pub.")

        try:
            skip_next_pub(person)
        except TombstoneAlreadyExistsError:
            pass  # Already skipped, so there is nothing more to do.

        return self.render_fragments(request, person, target="next")


class UndoSkipNextPubView(AutoPubFragmentsMixin, View):
    def post(self, request: HttpRequest) -> http.HttpResponse:
        person = self.post_checks(request)
        undo_skip_next_pub(person)
        return self.render_fragments(request, person, target="next")


class SetAutoPubView(AutoPubFragmentsMixin, View):
    def post(self, request: HttpRequest) -> http.HttpResponse:
        person = self.post_checks(request)

        enabled = request.POST.get("enabled")
        if enabled not in ("0", "1"):
            raise SuspiciousOperation("That request is not valid.")

        set_autopub(person, enabled=enabled == "1")
        return self.render_fragments(request, person, target="autopub")


class PubListView(LoginRequiredMixin, BreadcrumbsMixin, ListView):
    template_name = "pub/pub_list.html"

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [(reverse("pub:overview"), "Pub"), (None, "Pubs")]

    def get_queryset(self) -> QuerySet[Pub]:
        assert self.request.user.is_authenticated
        return get_listed_pubs(self.request.user)


class PubCreateView(LoginRequiredMixin, PermissionRequiredMixin, BreadcrumbsMixin, CreateView):
    template_name = "pub/pub_form.html"
    model = Pub
    form_class = PubForm
    permission_required = "pub.create_pub"
    success_url = reverse_lazy("pub:pubs-list")

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [
            (reverse("pub:overview"), "Pub"),
            (reverse("pub:pubs-list"), "Pubs"),
            (None, "New Pub"),
        ]

    def form_valid(self, form: PubForm) -> http.HttpResponse:
        messages.success(self.request, f"Added {form.instance.name}.")
        return super().form_valid(form)


class PubUpdateView(LoginRequiredMixin, PermissionRequiredMixin, BreadcrumbsMixin, UpdateView):
    template_name = "pub/pub_form.html"
    form_class = PubForm
    permission_required = "pub.edit_pub"
    success_url = reverse_lazy("pub:pubs-list")

    def get_queryset(self) -> QuerySet[Pub]:
        assert self.request.user.is_authenticated
        return Pub.objects.for_user(self.request.user).active()

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [
            (reverse("pub:overview"), "Pub"),
            (reverse("pub:pubs-list"), "Pubs"),
            (None, f"Edit {self.object.name}"),
        ]

    def form_valid(self, form: PubForm) -> http.HttpResponse:
        messages.success(self.request, f"Updated {form.instance.name}.")
        return super().form_valid(form)


class SetDefaultPubView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: UUID) -> http.HttpResponse:
        assert request.user.is_authenticated

        if not request.htmx:
            raise SuspiciousOperation("That request is not valid.")

        if not request.user.has_perm("pub.set_default_pub"):
            raise PermissionDenied("Only admins can choose the default pub.")

        pub = get_object_or_404(Pub.objects.for_user(request.user).active(), id=pk)
        pub.is_default = True
        pub.save()  # Saving a new default demotes the previous one.

        return render(
            request,
            "pub/inc/pubs_table.html",
            {"pubs": get_listed_pubs(request.user), "show_actions": True},
        )
