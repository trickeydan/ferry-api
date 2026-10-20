from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import User
from ferry.conftest import APITest
from ferry.pub.models import Pub


@pytest.mark.django_db
class TestPubEventCreateEndpoint(APITest):
    def test_post_with_pub_id(self, client: Client, admin_user: User) -> None:
        pub = Pub.objects.create(
            name="The Test Pub",
            emoji="🍺",
            map_url="https://example.com/map",
        )
        created_by = PersonFactory()

        response = client.post(
            reverse("api-2.0.0:events-list"),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={
                "timestamp": "2026-10-22T20:00:00+01:00",
                "pub": str(pub.id),
                "discord_id": 1562062687922294824,
                "table": None,
                "created_by": str(created_by.id),
            },
        )

        assert response.status_code == HTTPStatus.CREATED
        assert response.json()["pub"] == {
            "id": str(pub.id),
            "name": pub.name,
            "emoji": pub.emoji,
            "map_url": pub.map_url,
            "menu_url": "",
            "booking_url": "",
        }
