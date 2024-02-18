from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.conftest import GetAPIToken

if TYPE_CHECKING:
    from ferry.accounts.models import User


@pytest.mark.django_db
class TestUserInfoEndpoint:
    url = reverse_lazy("api-1.0.0:users_me")

    def test_get_missing_auth_header(self, client: Client) -> None:
        resp = client.get(self.url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_bad_auth_header(self, client: Client) -> None:
        resp = client.get(self.url, headers={"Authorization": "Bearer bees"})
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get(self, client: Client, user_with_person: User, get_api_token: GetAPIToken) -> None:
        # Arrange
        api_token = get_api_token(user_with_person)

        # Act
        resp = client.get(self.url, headers={"Authorization": f"Bearer {api_token.token}"})

        # Assert
        assert resp.status_code == HTTPStatus.OK
        assert resp.json() == {"username": user_with_person.username}
