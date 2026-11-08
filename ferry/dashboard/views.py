from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models.functions import DenseRank
from django.urls import reverse
from django.views.generic import ListView, TemplateView

from ferry.accounts.models import Person, PersonQuerySet, User
from ferry.core.mixins import BreadcrumbsMixin
from ferry.court.models import Accusation, Consequence
from ferry.pub.repository import get_next_pub_summary


def get_scoreboard(user: User) -> PersonQuerySet:
    qs = Person.objects.for_user(user)
    qs = qs.with_current_score()
    qs = qs.with_num_ratified_accusations()
    qs = qs.annotate(rank=models.Window(expression=DenseRank(), order_by=models.F("current_score").desc()))
    qs = qs.filter(models.Q(current_score__gt=0) | models.Q(num_ratified_accusations__gt=0))

    qs = qs.order_by("rank", "-current_score", "-num_ratified_accusations")
    return qs


def get_recent_accusations(user: User) -> models.QuerySet[Accusation]:
    qs = Accusation.objects.for_user(user)
    qs = qs.select_related("created_by", "suspect", "ratification__created_by", "ratification__consequence")
    qs = qs.order_by("-created_at")
    return qs


class HomeView(LoginRequiredMixin, BreadcrumbsMixin, TemplateView):
    template_name = "dashboard/home.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        assert self.request.user.is_authenticated

        return super().get_context_data(
            scoreboard=get_scoreboard(self.request.user)[:3],
            latest_accusation=get_recent_accusations(self.request.user).first(),
            **get_next_pub_summary(self.request.user.person),
            **kwargs,
        )


class FerriesOverviewView(LoginRequiredMixin, BreadcrumbsMixin, TemplateView):
    breadcrumbs = [(None, "Ferries")]
    template_name = "dashboard/ferries_overview.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        assert self.request.user.is_authenticated

        my_consequences = Consequence.objects.none()
        if self.request.user.person:
            my_consequences = (
                Consequence.objects.for_user(self.request.user)
                .filter(created_by=self.request.user.person, is_enabled=True)
                .annotate(victim_count=models.Count("ratifications"))
                .order_by("content")[:5]
            )

        return super().get_context_data(
            scoreboard=get_scoreboard(self.request.user)[:5],
            recent_accusations=get_recent_accusations(self.request.user)[:3],
            my_consequences=my_consequences,
            **kwargs,
        )


class ScoreboardView(LoginRequiredMixin, BreadcrumbsMixin, ListView):
    template_name = "dashboard/scoreboard.html"

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [(reverse("dashboard:ferries-overview"), "Ferries"), (None, "Scoreboard")]

    def get_queryset(self) -> PersonQuerySet:
        assert self.request.user.is_authenticated
        return get_scoreboard(self.request.user)


class ScoreHistoryView(LoginRequiredMixin, BreadcrumbsMixin, TemplateView):
    template_name = "dashboard/score-history.html"

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [(reverse("dashboard:ferries-overview"), "Ferries"), (None, "Score History")]


class RecentAccusationsView(LoginRequiredMixin, BreadcrumbsMixin, ListView):
    template_name = "dashboard/recent-accusations.html"
    paginate_by = 20

    def get_breadcrumbs(self) -> list[tuple[str | None, str]]:
        return super().get_breadcrumbs() + [(reverse("dashboard:ferries-overview"), "Ferries"), (None, "Accusations")]

    def get_queryset(self) -> models.QuerySet[Any]:
        assert self.request.user.is_authenticated
        return get_recent_accusations(self.request.user)
