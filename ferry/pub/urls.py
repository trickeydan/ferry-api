from django.urls import path

from . import views

app_name = "pub"

urlpatterns = [
    path("events", views.PubEventListView.as_view(), name="events-list"),
    path("events/<uuid:pk>/", views.PubEventDetailView.as_view(), name="events-detail"),
    path("events/<uuid:pk>/rsvp/", views.PubEventManualRSVPView.as_view(), name="events-manual-rsvp"),
    path("event/<uuid:pk>/booking/add/", views.AddPubEventBookingView.as_view(), name="events-add-booking"),
    path("event/<uuid:pk>/update-response/", views.UpdatePubEventResponseView.as_view(), name="events-update-response"),
]
