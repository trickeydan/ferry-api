from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models.functions import DenseRank
from django.views.generic import ListView

from .models import Person, PersonQuerySet


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
