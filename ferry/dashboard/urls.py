from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.ScoreboardView.as_view(), name="scoreboard"),
    path("accusations/", views.RecentAccusationsView.as_view(), name="recent-accusations"),
]
