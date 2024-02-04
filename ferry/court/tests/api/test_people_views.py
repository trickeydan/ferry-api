from http import HTTPStatus
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import APIToken
from ferry.court.factories import PersonFactory


@pytest.mark.django_db
class TestPeopleListEndpoint:
    url = reverse_lazy("api-1.0.0:people_list")

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self.url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_no_results(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self.url, headers={"Authorization": f"Bearer {api_token.token}"})
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"items": [], "count": 0}

    def test_get(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        expected_ids = [str(PersonFactory().id) for _ in range(10)]

        # Act
        resp = client.get(self.url, headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["count"] == 10
        assert len(data["items"]) == 10
        actual_items = [item["id"] for item in data["items"]]
        assert sorted(actual_items) == sorted(expected_ids)


@pytest.mark.django_db
class TestPeopleDetailEndpoint:
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:people_detail", args=[person_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers={"Authorization": f"Bearer {api_token.token}"})
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.get(self._get_url(person.id), headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(person.id)
        assert data["display_name"] == person.display_name
        assert data["discord_id"] == person.discord_id


@pytest.mark.django_db
class TestPeopleDetailByDiscordIDEndpoint:
    def _get_url(self, discord_id: int) -> str:
        return reverse_lazy("api-1.0.0:people_detail_by_discord_id", args=[discord_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(12))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self._get_url(12), headers={"Authorization": f"Bearer {api_token.token}"})
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        person = PersonFactory(discord_id=1234567)

        # Act
        resp = client.get(self._get_url(1234567), headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(person.id)
        assert data["display_name"] == person.display_name
        assert data["discord_id"] == person.discord_id
