from django.urls import path

from . import views

app_name = "court"

urlpatterns = [
    path("", views.ScoreboardView.as_view(), name="scoreboard"),
    path("scores/<uuid:pk>/", views.PersonScoreView.as_view(), name="person_score"),
    path("accusations/", views.RecentAccusationsView.as_view(), name="recent-accusations"),
    path("consequences/", views.ConsequenceListView.as_view(), name="consequence-list"),
    path("consequences/new/", views.ConsequenceCreateView.as_view(), name="consequence-create"),
]
