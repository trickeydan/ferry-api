from http import HTTPStatus
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import APIToken
from ferry.court.factories import ConsequenceFactory
from ferry.court.models import Consequence


@pytest.mark.django_db
class TestConsequenceListEndpoint:
    url = reverse_lazy("api-1.0.0:consequence_list")

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
        expected_ids = [str(ConsequenceFactory().id) for _ in range(10)]

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
class TestConsequenceDetailEndpoint:
    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:consequence_detail", args=[consequence_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers={"Authorization": f"Bearer {api_token.token}"})
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        consequence = ConsequenceFactory()

        # Act
        resp = client.get(self._get_url(consequence.id), headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(consequence.id)
        assert data["content"] == consequence.content
        assert data["is_enabled"] == consequence.is_enabled
        assert data["created_by"] == {
            "id": str(consequence.created_by.id),
            "display_name": consequence.created_by.display_name,
        }


@pytest.mark.django_db
class TestConsequencesDeleteEndpoint:
    def _get_headers(self, api_token: APIToken) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:consequence_delete", args=[consequence_id])

    def test_delete_unauthenticated(self, client: Client) -> None:
        resp = client.delete(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.delete(self._get_url(UUID(int=0)), headers=self._get_headers(api_token))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        consequence = ConsequenceFactory()
        consequence_id = consequence.id

        # Act
        resp = client.delete(self._get_url(consequence.id), headers=self._get_headers(api_token))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"success": True}

        assert not Consequence.objects.filter(id=consequence_id).exists()
