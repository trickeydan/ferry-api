from http import HTTPStatus
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import APIToken
from ferry.court.factories import AccusationFactory


@pytest.mark.django_db
class TestRatificationDetailEndpoint:
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:ratification_detail", args=[accusation_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers={"Authorization": f"Bearer {api_token.token}"})
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get_unratified(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        accusation = AccusationFactory()

        # Act
        resp = client.get(self._get_url(accusation.id), headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["id"] == str(accusation.ratification.id)
        assert data["consequence"] == {
            "id": str(accusation.ratification.consequence.id),
            "content": accusation.ratification.consequence.content,
        }
        assert data["created_by"] == {
            "id": str(accusation.ratification.created_by.id),
            "display_name": accusation.ratification.created_by.display_name,
        }
