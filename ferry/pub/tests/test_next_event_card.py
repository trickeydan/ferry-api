from datetime import timedelta
from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ferry.accounts.models import Person, User
from ferry.pub.models import Pub, PubEvent, PubEventRSVP, PubEventRSVPMethod


@pytest.mark.django_db
class TestScoreboardNextEventCard:
    url = reverse("dashboard:scoreboard")

    def create_next_event(self, person: Person) -> PubEvent:
        pub = Pub.objects.create(name="The Anchor", emoji="🍺", map_url="https://example.com/map")
        return PubEvent.objects.create(timestamp=timezone.now() + timedelta(days=2), pub=pub, created_by=person)

    def test_no_next_event(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["next_event"] is None
        assert b"hasn't been decided yet" in response.content

    def test_next_event_without_response(self, client: Client, user_with_person: User, person: Person) -> None:
        event = self.create_next_event(person)
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert response.context["next_event"] == event
        assert reverse("pub:events-detail", args=[event.id]).encode() in response.content
        assert b"You haven't responded yet" in response.content

    def test_next_event_going(self, client: Client, user_with_person: User, person: Person) -> None:
        event = self.create_next_event(person)
        PubEventRSVP.objects.create(pub_event=event, person=person, is_attending=True, method=PubEventRSVPMethod.WEB)
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert response.context["next_event_attendee_count"] == 1
        assert b"You're going" in response.content
