from http import HTTPStatus
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import User
from ferry.api_legacy.tests.utils import APITest
from ferry.core.discord import NoSuchGuildMemberError
from ferry.court.factories import AccusationFactory, PersonFactory
from ferry.court.models import Person


@pytest.mark.django_db
class TestPeopleListEndpoint(APITest):
    url = reverse_lazy("api-1.0.0:people_list")

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self.url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_no_results(self, client: Client, admin_user: User) -> None:
        resp = client.get(self.url, headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"items": [], "count": 0}

    def test_get(self, client: Client, admin_user: User) -> None:
        # Arrange
        expected_ids = [str(PersonFactory().id) for _ in range(10)]

        # Act
        resp = client.get(self.url, headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["count"] == 10
        assert len(data["items"]) == 10
        actual_items = [item["id"] for item in data["items"]]
        assert sorted(actual_items) == sorted(expected_ids)


@pytest.mark.django_db
class TestPeopleCreateEndpoint(APITest):
    def _get_url(self) -> str:
        return reverse_lazy("api-1.0.0:people_create")

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url())
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                [
                    {"type": "missing", "loc": ["body", "payload", "display_name"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "discord_id"], "msg": "Field required"},
                ],
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                [
                    {"type": "missing", "loc": ["body", "payload", "display_name"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "discord_id"], "msg": "Field required"},
                ],
                id="spurious",
            ),
            pytest.param(
                {"display_name": "name"},
                [
                    {"type": "missing", "loc": ["body", "payload", "discord_id"], "msg": "Field required"},
                ],
                id="missing_discord_id",
            ),
            pytest.param(
                {"discord_id": 1234},
                [
                    {"type": "missing", "loc": ["body", "payload", "display_name"], "msg": "Field required"},
                ],
                id="missing_display_name",
            ),
            pytest.param(
                {"display_name": 1234, "discord_id": "a string"},
                [
                    {
                        "type": "string_type",
                        "loc": ["body", "payload", "display_name"],
                        "msg": "Input should be a valid string",
                    },
                    {
                        "type": "int_parsing",
                        "loc": ["body", "payload", "discord_id"],
                        "msg": "Input should be a valid integer, unable to parse string as an integer",
                    },
                ],
                id="bad_types",
            ),
        ],
    )
    def test_post_bad_payload(
        self, client: Client, admin_user: User, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": errors,
        }

    def test_post_no_permission(self, client: Client, user_with_person: User) -> None:
        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"display_name": "bees", "discord_id": None},
        )

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 403,
            "status_name": "FORBIDDEN",
            "detail": "You don't have permission to perform that action",
        }

    @pytest.mark.parametrize(
        ("payload", "expected_display_name", "expected_discord_id"),
        [
            pytest.param({"display_name": "bees", "discord_id": None}, "bees", None, id="remove-discord"),
            pytest.param({"display_name": "wasps", "discord_id": 9876543210}, "wasps", 9876543210, id="update-both"),
        ],
    )
    @patch("ferry.court.models.get_discord_client")
    def test_post(
        self,
        mock_get_discord_client: Mock,
        client: Client,
        admin_user: User,
        payload: dict,
        expected_display_name: str | None,
        expected_discord_id: int | None,
    ) -> None:
        # Arrange
        mock_get_guild_member_by_id = mock_get_discord_client.return_value.get_guild_member_by_id
        mock_get_guild_member_by_id.return_value = {}

        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"]
        assert data["display_name"] == expected_display_name
        assert data["discord_id"] == expected_discord_id
        assert data["current_score"] == 0

        person = Person.objects.get(id=data["id"])
        assert person.display_name == expected_display_name
        assert person.discord_id == expected_discord_id

    @patch("ferry.court.models.get_discord_client")
    def test_post_no_such_discord_user(
        self,
        mock_get_discord_client: Mock,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        mock_get_guild_member_by_id = mock_get_discord_client.return_value.get_guild_member_by_id
        mock_get_guild_member_by_id.side_effect = NoSuchGuildMemberError

        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"display_name": "wasps", "discord_id": 9876543210},
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert resp.json() == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [{"detail": ["Unknown discord ID. Is the user part of the guild?"], "loc": "__all__"}],
        }


@pytest.mark.django_db
class TestPeopleDetailEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:people_detail", args=[person_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, admin_user: User) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, client: Client, admin_user: User) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.get(self._get_url(person.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(person.id)
        assert data["display_name"] == person.display_name
        assert data["discord_id"] == person.discord_id
        assert data["current_score"] == 0

    def test_get_with_score(self, client: Client, admin_user: User) -> None:
        # Arrange
        person = PersonFactory()
        AccusationFactory.create_batch(size=15, suspect=person)

        # Act
        resp = client.get(self._get_url(person.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(person.id)
        assert data["display_name"] == person.display_name
        assert data["discord_id"] == person.discord_id
        assert data["current_score"] == 15


@pytest.mark.django_db
class TestPeopleDetailByDiscordIDEndpoint(APITest):
    def _get_url(self, discord_id: int) -> str:
        return reverse_lazy("api-1.0.0:people_detail_by_discord_id", args=[discord_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(12))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, admin_user: User) -> None:
        resp = client.get(self._get_url(12), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, client: Client, admin_user: User) -> None:
        # Arrange
        person = PersonFactory(discord_id=1234567)

        # Act
        resp = client.get(self._get_url(1234567), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(person.id)
        assert data["display_name"] == person.display_name
        assert data["discord_id"] == person.discord_id
        assert data["current_score"] == 0


@pytest.mark.django_db
class TestPeopleUpdateEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:people_update", args=[person_id])

    def test_put_unauthenticated(self, client: Client) -> None:
        resp = client.put(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_put_404(self, client: Client, admin_user: User) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_put_no_payload(self, client: Client, admin_user: User) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.put(self._get_url(person.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [{"type": "missing", "loc": ["body", "payload"], "msg": "Field required"}],
        }

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                [
                    {"type": "missing", "loc": ["body", "payload", "display_name"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "discord_id"], "msg": "Field required"},
                ],
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                [
                    {"type": "missing", "loc": ["body", "payload", "display_name"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "discord_id"], "msg": "Field required"},
                ],
                id="spurious",
            ),
            pytest.param(
                {"display_name": "name"},
                [
                    {"type": "missing", "loc": ["body", "payload", "discord_id"], "msg": "Field required"},
                ],
                id="missing_discord_id",
            ),
            pytest.param(
                {"discord_id": 1234},
                [
                    {"type": "missing", "loc": ["body", "payload", "display_name"], "msg": "Field required"},
                ],
                id="missing_display_name",
            ),
            pytest.param(
                {"display_name": 1234, "discord_id": "a string"},
                [
                    {
                        "type": "string_type",
                        "loc": ["body", "payload", "display_name"],
                        "msg": "Input should be a valid string",
                    },
                    {
                        "type": "int_parsing",
                        "loc": ["body", "payload", "discord_id"],
                        "msg": "Input should be a valid integer, unable to parse string as an integer",
                    },
                ],
                id="bad_types",
            ),
        ],
    )
    def test_put_bad_payload(
        self, client: Client, admin_user: User, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.put(
            self._get_url(person.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {"status": "error", "status_code": 422, "status_name": "UNPROCESSABLE_ENTITY", "detail": errors}

    def _test_put(
        self,
        client: Client,
        user: User,
        person: Person,
        payload: dict,
        expected_display_name: str | None,
        expected_discord_id: int | None,
    ) -> None:
        # Act
        resp = client.put(
            self._get_url(person.id),
            headers=self.get_headers(user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(person.id)
        assert data["display_name"] == expected_display_name
        assert data["discord_id"] == expected_discord_id
        assert data["current_score"] == 0

        person.refresh_from_db()
        assert person.display_name == expected_display_name
        assert person.discord_id == expected_discord_id

    @pytest.mark.parametrize(
        ("payload", "expected_display_name", "expected_discord_id"),
        [
            pytest.param({"display_name": "bees", "discord_id": None}, "bees", None, id="remove-discord"),
            pytest.param({"display_name": "wasps", "discord_id": 9876543210}, "wasps", 9876543210, id="update-both"),
        ],
    )
    @patch("ferry.court.models.get_discord_client")
    def test_put_admin(
        self,
        mock_get_discord_client: Mock,
        client: Client,
        admin_user: User,
        payload: dict,
        expected_display_name: str | None,
        expected_discord_id: int | None,
    ) -> None:
        mock_get_guild_member_by_id = mock_get_discord_client.return_value.get_guild_member_by_id
        mock_get_guild_member_by_id.return_value = {}
        person = PersonFactory(display_name="bees", discord_id=1234567890)

        self._test_put(client, admin_user, person, payload, expected_display_name, expected_discord_id)

    @patch("ferry.court.models.get_discord_client")
    def test_put(
        self,
        mock_get_discord_client: Mock,
        client: Client,
        user_with_person: User,
    ) -> None:
        # Arrange
        # We are not updating the ID here as we have no permission
        assert user_with_person.person is not None
        user_with_person.person.discord_id = 9876543210
        user_with_person.person.save(update_fields=["discord_id"])

        mock_get_guild_member_by_id = mock_get_discord_client.return_value.get_guild_member_by_id
        mock_get_guild_member_by_id.return_value = {}

        self._test_put(
            client,
            user_with_person,
            user_with_person.person,
            payload={"display_name": "wasps", "discord_id": 9876543210},
            expected_display_name="wasps",
            expected_discord_id=9876543210,
        )

    @patch("ferry.court.models.get_discord_client")
    def test_put_no_such_discord_user(
        self,
        mock_get_discord_client: Mock,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        mock_get_guild_member_by_id = mock_get_discord_client.return_value.get_guild_member_by_id
        mock_get_guild_member_by_id.side_effect = NoSuchGuildMemberError
        person = PersonFactory(display_name="bees", discord_id=1234567890)

        # Act
        resp = client.put(
            self._get_url(person.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"display_name": "wasps", "discord_id": 9876543210},
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert resp.json() == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [{"detail": ["Unknown discord ID. Is the user part of the guild?"], "loc": "__all__"}],
        }

    def test_put_cannot_edit_other_user(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        # Arrange
        person = PersonFactory(display_name="bees", discord_id=1234567890)

        # Act
        resp = client.put(
            self._get_url(person.id),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"display_name": "wasps", "discord_id": None},
        )

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        assert resp.json() == {
            "status": "error",
            "status_code": 403,
            "status_name": "FORBIDDEN",
            "detail": "You don't have permission to perform that action",
        }

    def test_put_cannot_edit_discord_id(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        # Arrange
        assert user_with_person.person is not None

        # Act
        resp = client.put(
            self._get_url(user_with_person.person.id),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"display_name": "wasps", "discord_id": 1234},
        )

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        assert resp.json() == {
            "status": "error",
            "status_code": 403,
            "status_name": "FORBIDDEN",
            "detail": "You don't have permission to update a Discord ID directly.",
        }


@pytest.mark.django_db
class TestPeopleDeleteEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:people_delete", args=[person_id])

    def test_delete_unauthenticated(self, client: Client) -> None:
        resp = client.delete(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_404(self, client: Client, admin_user: User) -> None:
        resp = client.delete(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, client: Client, admin_user: User) -> None:
        # Arrange
        person = PersonFactory()
        person_id = person.id

        # Act
        resp = client.delete(self._get_url(person.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"status": "success"}

        assert not Person.objects.filter(id=person_id).exists()

    def test_delete_no_permission(self, client: Client, user_with_person: User) -> None:
        # Arrange
        person = PersonFactory()
        person_id = person.id

        # Act
        resp = client.delete(self._get_url(person_id), headers=self.get_headers(user_with_person))

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 403,
            "status_name": "FORBIDDEN",
            "detail": "You don't have permission to perform that action",
        }

        assert Person.objects.filter(id=person_id).exists()
