from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models.functions import DenseRank
from django.views.generic import ListView

from ferry.accounts.models import Person, PersonQuerySet
from ferry.court.models import Accusation


class ScoreboardView(LoginRequiredMixin, ListView):
    template_name = "court/scoreboard.html"

    def get_queryset(self) -> PersonQuerySet:
        assert self.request.user.is_authenticated
        qs = Person.objects.for_user(self.request.user)
        qs = qs.with_current_score()
        qs = qs.with_num_ratified_accusations()
        qs = qs.annotate(rank=models.Window(expression=DenseRank(), order_by=models.F("current_score").desc()))
        qs = qs.filter(models.Q(current_score__gt=0) | models.Q(num_ratified_accusations__gt=0))

        qs = qs.order_by("rank", "-current_score", "-num_ratified_accusations")
        return qs


class RecentAccusationsView(LoginRequiredMixin, ListView):
    template_name = "court/recent-accusations.html"

    def get_queryset(self) -> models.QuerySet[Any]:
        assert self.request.user.is_authenticated
        qs = Accusation.objects.for_user(self.request.user)
        qs = qs.order_by("-created_at")
        return qs
