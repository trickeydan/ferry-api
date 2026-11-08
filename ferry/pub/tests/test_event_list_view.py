from datetime import timedelta
from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ferry.accounts.models import Person, User
from ferry.pub.models import Pub, PubEvent


@pytest.mark.django_db
class TestPubEventListView:
    url = reverse("pub:events-list")

    def create_events(self, person: Person, count: int) -> None:
        pub = Pub.objects.create(name="Pub", emoji="🍺", map_url="https://example.com/map")
        now = timezone.now()
        PubEvent.objects.bulk_create(
            PubEvent(timestamp=now - timedelta(days=i + 1), pub=pub, created_by=person) for i in range(count)
        )

    def test_paginates_events(self, client: Client, user_with_person: User, person: Person) -> None:
        self.create_events(person, 25)
        client.force_login(user_with_person)

        first = client.get(self.url)
        second = client.get(self.url, {"page": 2})

        assert first.status_code == HTTPStatus.OK
        assert len(first.context["object_list"]) == 20
        assert first.context["is_paginated"]
        assert len(second.context["object_list"]) == 5

    def test_no_pagination_controls_for_single_page(
        self, client: Client, user_with_person: User, person: Person
    ) -> None:
        self.create_events(person, 3)
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert not response.context["is_paginated"]
        assert b'aria-label="Pagination"' not in response.content
