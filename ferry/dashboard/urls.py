from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.ScoreboardView.as_view(), name="scoreboard"),
    path("score-history/", views.ScoreHistoryView.as_view(), name="score-history"),
    path("accusations/", views.RecentAccusationsView.as_view(), name="recent-accusations"),
]
