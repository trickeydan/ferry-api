from django.urls import path
from django.views.generic import RedirectView

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("ferries/", views.FerriesOverviewView.as_view(), name="ferries-overview"),
    path("ferries/scoreboard/", views.ScoreboardView.as_view(), name="scoreboard"),
    path("ferries/score-history/", views.ScoreHistoryView.as_view(), name="score-history"),
    path("ferries/accusations/", views.RecentAccusationsView.as_view(), name="recent-accusations"),
    # Legacy URLs from before the Ferries section existed.
    path("score-history/", RedirectView.as_view(pattern_name="dashboard:score-history", permanent=True)),
    path("accusations/", RedirectView.as_view(pattern_name="dashboard:recent-accusations", permanent=True)),
]
