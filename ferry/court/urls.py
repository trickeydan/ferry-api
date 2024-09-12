from django.urls import path

from . import views

app_name = "court"

urlpatterns = [
    path("", views.ScoreboardView.as_view(), name="scoreboard"),
    path("scores/<uuid:pk>/", views.PersonScoreView.as_view(), name="person_score"),
]
