from typing import Any, cast

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models.functions import DenseRank
from django.views.generic import DetailView, ListView

from .models import Accusation, Person, PersonQuerySet


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
