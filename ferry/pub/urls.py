from django.urls import path

from . import views

app_name = "pub"

urlpatterns = [
    path("", views.PubOverviewView.as_view(), name="overview"),
    path("skip/", views.SkipNextPubView.as_view(), name="skip-next"),
    path("skip/undo/", views.UndoSkipNextPubView.as_view(), name="undo-skip-next"),
    path("autopub/", views.SetAutoPubView.as_view(), name="autopub"),
    path("events", views.PubEventListView.as_view(), name="events-list"),
    path("events/<uuid:pk>/", views.PubEventDetailView.as_view(), name="events-detail"),
    path("events/<uuid:pk>/rsvp/", views.PubEventManualRSVPView.as_view(), name="events-manual-rsvp"),
    path("event/<uuid:pk>/booking/add/", views.AddPubEventBookingView.as_view(), name="events-add-booking"),
    path("event/<uuid:pk>/update-response/", views.UpdatePubEventResponseView.as_view(), name="events-update-response"),
]
