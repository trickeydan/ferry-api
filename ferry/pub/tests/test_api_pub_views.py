import pytest
from django.test import Client
from django.urls import reverse

from ferry.accounts.models import User
from ferry.conftest import APITest
from ferry.pub.models import Pub


@pytest.mark.django_db
class TestPubListEndpoint(APITest):
    def test_filter_by_is_default(self, client: Client, admin_user: User) -> None:
        default = Pub.objects.create(name="Default", emoji="🍺", map_url="https://example.com/a", is_default=True)
        Pub.objects.create(name="Other", emoji="🍻", map_url="https://example.com/b")

        response = client.get(
            reverse("api-2.0.0:pubs-list"),
            {"is_default": "true"},
            headers=self.get_headers(admin_user),
        )

        assert [pub["id"] for pub in response.json()["results"]] == [str(default.id)]
