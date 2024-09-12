from django.urls import path

from . import views

app_name = "court"

urlpatterns = [
    path("", views.ScoreboardView.as_view(), name="scoreboard"),
]
