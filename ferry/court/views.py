from typing import Any, cast

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models.functions import DenseRank
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView

from ferry.accounts.models import Person, PersonQuerySet
from ferry.court.forms import ConsequenceCreateForm

from .models import Accusation, Consequence


class ScoreboardView(LoginRequiredMixin, ListView):
    template_name = "court/scoreboard.html"

    def get_queryset(self) -> PersonQuerySet:
        assert self.request.user.is_authenticated
        qs = Person.objects.for_user(self.request.user)
        qs = qs.with_current_score()
        qs = qs.with_num_ratified_accusations()
        qs = qs.annotate(rank=models.Window(expression=DenseRank(), order_by=models.F("current_score").desc()))

        qs = qs.order_by("rank", "-current_score", "-num_ratified_accusations")
        return qs


class PersonScoreView(LoginRequiredMixin, DetailView):
    model = Person
    template_name = "court/person.html"

    def get_queryset(self) -> PersonQuerySet:
        qs = cast(PersonQuerySet, super().get_queryset())
        qs = qs.with_current_score()
        qs = qs.with_num_ratified_accusations()
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        assert self.request.user.is_authenticated
        qs = Accusation.objects.for_user(self.request.user)
        qs = qs.filter(models.Q(suspect=self.object) | models.Q(created_by=self.object))
        qs = qs.order_by("-created_at")

        return super().get_context_data(accusations=qs, **kwargs)


class RecentAccusationsView(LoginRequiredMixin, ListView):
    template_name = "court/recent-accusations.html"

    def get_queryset(self) -> models.QuerySet[Any]:
        assert self.request.user.is_authenticated
        qs = Accusation.objects.for_user(self.request.user)
        qs = qs.order_by("-created_at")
        return qs


class ConsequenceListView(LoginRequiredMixin, ListView):
    template_name = "court/consequence_list.html"

    def get_queryset(self) -> models.QuerySet[Any]:
        assert self.request.user.is_authenticated
        qs = Consequence.objects.for_user(self.request.user)

        # Apply additional filter for superusers.
        qs = qs.filter(created_by=self.request.user.person)

        qs = qs.annotate(victim_count=models.Count("ratifications"))
        qs = qs.order_by("-is_enabled", "content")
        return qs


class ConsequenceCreateView(LoginRequiredMixin, CreateView):
    template_name = "court/consequence_create.html"
    model = Consequence
    form_class = ConsequenceCreateForm
    success_url = reverse_lazy("court:consequence-list")

    def get_form_kwargs(self) -> dict[str, Any]:
        assert self.request.user.is_authenticated
        assert self.request.user.person

        kwargs = super().get_form_kwargs()
        kwargs["person"] = self.request.user.person
        return kwargs

    def form_valid(self, form: ConsequenceCreateForm) -> HttpResponse:
        messages.info(self.request, "Successfully created consequence.")
        return super().form_valid(form)
