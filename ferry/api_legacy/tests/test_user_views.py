from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.api_legacy.tests.utils import APITest

if TYPE_CHECKING:
    from ferry.accounts.models import User


@pytest.mark.django_db
class TestUserInfoEndpoint(APITest):
    url = reverse_lazy("api-1.0.0:users_me")

    def test_get_missing_auth_header(self, client: Client) -> None:
        resp = client.get(self.url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_bad_auth_header(self, client: Client) -> None:
        resp = client.get(self.url, headers={"Authorization": "Bearer bees"})
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_with_person(self, client: Client, user_with_person: User) -> None:
        # Act
        assert user_with_person.person is not None
        resp = client.get(self.url, headers=self.get_headers(user_with_person))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        assert resp.json() == {
            "username": user_with_person.username,
            "person": {
                "id": str(user_with_person.person.id),
                "display_name": user_with_person.person.display_name,
            },
        }

    def test_get_no_person(self, client: Client, admin_user: User) -> None:
        # Act
        resp = client.get(self.url, headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        assert resp.json() == {"username": admin_user.username, "person": None}
