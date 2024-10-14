from typing import Any
from uuid import UUID

from django import http
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import SuspiciousOperation
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, View

from ferry.core.http import HttpRequest
from ferry.core.mixins import BreadcrumbsMixin
from ferry.court.forms import ConsequenceCreateForm

from .models import Consequence


class ConsequenceListView(LoginRequiredMixin, BreadcrumbsMixin, ListView):
    template_name = "court/consequence_list.html"
    breadcrumbs = [(None, "Ferries"), (None, "My Consequences")]

    def get_queryset(self) -> models.QuerySet[Any]:
        assert self.request.user.is_authenticated
        qs = Consequence.objects.for_user(self.request.user)

        # Apply additional filter for superusers.
        qs = qs.filter(created_by=self.request.user.person)

        qs = qs.annotate(victim_count=models.Count("ratifications"))
        qs = qs.order_by("-is_enabled", "content")
        return qs


class ConsequenceCreateView(LoginRequiredMixin, BreadcrumbsMixin, CreateView):
    template_name = "court/consequence_create.html"
    model = Consequence
    form_class = ConsequenceCreateForm
    success_url = reverse_lazy("court:consequence-list")
    breadcrumbs = [
        (None, "Ferries"),
        (reverse_lazy("court:consequence-list"), "My Consequences"),
        (None, "New Consequence"),
    ]

    def get_form_kwargs(self) -> dict[str, Any]:
        assert self.request.user.is_authenticated
        assert self.request.user.person

        kwargs = super().get_form_kwargs()
        kwargs["person"] = self.request.user.person
        return kwargs

    def form_valid(self, form: ConsequenceCreateForm) -> HttpResponse:
        messages.info(self.request, "Successfully created consequence.")
        return super().form_valid(form)


class DeactivateConsequenceView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, pk: UUID) -> http.HttpResponse:
        assert request.user.is_authenticated

        if not request.htmx:
            raise SuspiciousOperation("That request is not valid.")

        qs = Consequence.objects.for_user(request.user)
        # Apply additional filter for superusers.
        qs = qs.filter(created_by=request.user.person)
        qs = qs.annotate(victim_count=models.Count("ratifications"))

        consequence = get_object_or_404(qs, id=pk)
        consequence.is_enabled = False
        consequence.save()

        return render(request, "court/consequence_list__table_row.html", {"consequence": consequence})
