from django.urls import path

from . import views

app_name = "pub"

urlpatterns = [
    path("events", views.PubEventListView.as_view(), name="events-list"),
    path("events/<uuid:pk>/", views.PubEventDetailView.as_view(), name="events-detail"),
]
