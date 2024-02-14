from http import HTTPStatus
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import APIToken
from ferry.court.factories import AccusationFactory


@pytest.mark.django_db
class TestAccusationListEndpoint:
    url = reverse_lazy("api-1.0.0:accusation_list")

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
        expected_ids = [str(AccusationFactory().id) for _ in range(10)]

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
class TestAccusationDetailEndpoint:
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:accusation_detail", args=[accusation_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers={"Authorization": f"Bearer {api_token.token}"})
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get_unratified(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.get(self._get_url(accusation.id), headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(accusation.id)
        assert data["quote"] == accusation.quote
        assert data["ratification"] is None
        assert data["suspect"] == {
            "id": str(accusation.suspect.id),
            "display_name": accusation.suspect.display_name,
        }
        assert data["created_by"] == {
            "id": str(accusation.created_by.id),
            "display_name": accusation.created_by.display_name,
        }

    def test_get_ratified(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        accusation = AccusationFactory()

        # Act
        resp = client.get(self._get_url(accusation.id), headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(accusation.id)
        assert data["quote"] == accusation.quote
        assert data["suspect"] == {
            "id": str(accusation.suspect.id),
            "display_name": accusation.suspect.display_name,
        }
        assert data["created_by"] == {
            "id": str(accusation.created_by.id),
            "display_name": accusation.created_by.display_name,
        }
        assert data["ratification"]["id"] == str(accusation.ratification.id)
        assert data["ratification"]["consequence"] == {
            "id": str(accusation.ratification.consequence.id),
            "content": accusation.ratification.consequence.content,
        }
        assert data["ratification"]["created_by"] == {
            "id": str(accusation.ratification.created_by.id),
            "display_name": accusation.ratification.created_by.display_name,
        }
