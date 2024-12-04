import base64
from http import HTTPStatus
from unittest.mock import Mock, patch
from uuid import UUID

import pytest
from django.core.signing import TimestampSigner
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import Person, User
from ferry.conftest import APITest
from ferry.core.discord import NoSuchGuildMemberError
from ferry.court.factories import AccusationFactory


@pytest.mark.django_db
class TestPeopleListEndpoint(APITest):
    url = reverse_lazy("api-2.0.0:people-list")

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self.url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_no_results(self, client: Client, admin_user: User) -> None:
        resp = client.get(self.url, headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"results": [], "next": None, "previous": None, "count": 0}

    def test_get(self, client: Client, admin_user: User) -> None:
        # Arrange
        expected_ids = [str(PersonFactory().id) for _ in range(10)]

        # Act
        resp = client.get(self.url, headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["count"] == 10
        assert len(data["results"]) == 10
        actual_results = [item["id"] for item in data["results"]]
        assert sorted(actual_results) == sorted(expected_ids)

    def test_get_ordering(self, client: Client, admin_user: User) -> None:
        # Arrange
        PersonFactory.create_batch(size=10)

        # Act
        resp = client.get(f"{self.url}?ordering=-display_name", headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        ids = [UUID(item["id"]) for item in data["results"]]
        expected_ids_in_order = Person.objects.order_by("-display_name").values_list("id", flat=True)
        assert ids == list(expected_ids_in_order)

    def test_get_filter_discord_id(self, client: Client, admin_user: User) -> None:
        # Arrange
        PersonFactory.create_batch(size=10)

        # Act
        resp = client.get(f"{self.url}?discord_id=12", headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["count"] == 0
        assert data["results"] == []

    def test_get_filter_discord_id_found(self, client: Client, admin_user: User) -> None:
        # Arrange
        PersonFactory.create_batch(size=10)
        person_with_discord = PersonFactory(discord_id=12345)

        # Act
        resp = client.get(f"{self.url}?discord_id=12345", headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["count"] == 1
        assert data["results"][0]["id"] == str(person_with_discord.id)


@pytest.mark.django_db
class TestPeopleCreateEndpoint(APITest):
    def _get_url(self) -> str:
        return reverse_lazy("api-2.0.0:people-list")

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url())
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                {"display_name": ["This field is required."]},
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                {"display_name": ["This field is required."]},
                id="spurious",
            ),
            pytest.param(
                {"discord_id": 1234},
                {"display_name": ["This field is required."]},
                id="missing_display_name",
            ),
            pytest.param(
                {"display_name": 1234, "discord_id": "a string"},
                {"discord_id": ["A valid integer is required."]},
                id="bad_types",
            ),
        ],
    )
    @patch("ferry.accounts.api.serializers.get_discord_client")
    def test_post_bad_payload(
        self,
        mock_get_discord_client: Mock,
        client: Client,
        admin_user: User,
        payload: dict[str, int],
        errors: list[dict],
    ) -> None:
        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == errors

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
            "detail": "You do not have permission to perform this action.",
        }

    @pytest.mark.parametrize(
        ("payload", "expected_display_name", "expected_discord_id"),
        [
            pytest.param({"display_name": "bees"}, "bees", None, id="missing-discord"),
            pytest.param({"display_name": "bees", "discord_id": None}, "bees", None, id="no-discord"),
            pytest.param({"display_name": "wasps", "discord_id": 9876543210}, "wasps", 9876543210, id="update-both"),
        ],
    )
    @patch("ferry.accounts.api.serializers.get_discord_client")
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
        assert resp.status_code == HTTPStatus.CREATED
        data = resp.json()
        assert data.keys() == {"id", "display_name", "discord_id", "created_at", "updated_at"}
        assert data["id"]
        assert data["display_name"] == expected_display_name
        assert data["discord_id"] == expected_discord_id

        person = Person.objects.get(id=data["id"])
        assert person.display_name == expected_display_name
        assert person.discord_id == expected_discord_id

    @patch("ferry.accounts.api.serializers.get_discord_client")
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
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        assert resp.json() == {"discord_id": ["Unknown discord ID. Is the user part of the guild?"]}


@pytest.mark.django_db
class TestPeopleDetailEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:people-detail", args=[person_id])

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
        assert data.keys() == {"id", "display_name", "discord_id", "current_score", "created_at", "updated_at"}
        assert data["id"] == str(person.id)
        assert data["display_name"] == person.display_name
        assert data["discord_id"] == person.discord_id
        assert data["current_score"] == "0.00"

    def test_get_with_score(self, client: Client, admin_user: User) -> None:
        # Arrange
        person = PersonFactory()
        AccusationFactory.create_batch(size=15, suspect=person)

        # Act
        resp = client.get(self._get_url(person.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data.keys() == {"id", "display_name", "discord_id", "current_score", "created_at", "updated_at"}
        assert data["id"] == str(person.id)
        assert data["display_name"] == person.display_name
        assert data["discord_id"] == person.discord_id
        assert data["current_score"] == "15.00"


@pytest.mark.django_db
class TestPeopleUpdateEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:people-detail", args=[person_id])

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
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"display_name": ["This field is required."]}

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                {"display_name": ["This field is required."]},
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                {"display_name": ["This field is required."]},
                id="spurious",
            ),
            pytest.param(
                {"discord_id": 1234},
                {"display_name": ["This field is required."]},
                id="missing_display_name",
            ),
            pytest.param(
                {"display_name": 1234, "discord_id": "a string"},
                {"discord_id": ["A valid integer is required."]},
                id="bad_types",
            ),
        ],
    )
    @patch("ferry.accounts.api.serializers.get_discord_client")
    def test_put_bad_payload(
        self,
        mock_get_discord_client: Mock,
        client: Client,
        admin_user: User,
        payload: dict[str, int],
        errors: list[dict],
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
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == errors

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
        assert data.keys() == {"id", "display_name", "discord_id", "current_score", "created_at", "updated_at"}
        assert data["id"] == str(person.id)
        assert data["display_name"] == expected_display_name
        assert data["discord_id"] == expected_discord_id

        person.refresh_from_db()
        assert person.display_name == expected_display_name
        assert person.discord_id == expected_discord_id

    @pytest.mark.parametrize(
        ("payload", "expected_display_name", "expected_discord_id"),
        [
            pytest.param({"display_name": "bees"}, "bees", 1234567890, id="no-discord"),
            pytest.param({"display_name": "bees", "discord_id": None}, "bees", None, id="remove-discord"),
            pytest.param({"display_name": "wasps", "discord_id": 9876543210}, "wasps", 9876543210, id="update-both"),
        ],
    )
    @patch("ferry.accounts.api.serializers.get_discord_client")
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

    @patch("ferry.accounts.api.serializers.get_discord_client")
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

    @patch("ferry.accounts.api.serializers.get_discord_client")
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
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        assert resp.json() == {"discord_id": ["Unknown discord ID. Is the user part of the guild?"]}

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
            "detail": "You do not have permission to perform this action.",
        }

    @patch("ferry.accounts.api.serializers.get_discord_client")
    def test_put_cannot_edit_discord_id(
        self,
        mock_get_discord_client: Mock,
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
        assert resp.json() == {"detail": "You don't have permission to update a Discord ID directly."}


@pytest.mark.django_db
class TestPeopleDeleteEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:people-detail", args=[person_id])

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
        assert resp.status_code == HTTPStatus.NO_CONTENT
        assert resp.content == b""

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
        assert data == {"detail": "You do not have permission to perform this action."}

        assert Person.objects.filter(id=person_id).exists()


@pytest.mark.django_db
class TestPeopleTokenEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:people-fact", args=[person_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, admin_user: User) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get_unauthorised(self, client: Client, user: User) -> None:
        person = PersonFactory()

        # Act
        resp = client.get(self._get_url(person.id), headers=self.get_headers(user))

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You don't have permission to get a FACT for that person."}

    def test_get(self, client: Client, user_with_person: User) -> None:
        assert user_with_person.person
        resp = client.get(self._get_url(user_with_person.person.id), headers=self.get_headers(user_with_person))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"link_token": None}

    def test_get_admin(self, client: Client, admin_user: User) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.get(self._get_url(person.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data.keys() == {"link_token"}

        link_token = data["link_token"]
        signer = TimestampSigner()
        assert signer.unsign(base64.b64decode(link_token).decode()) == str(person.id)

    def test_get_admin_already_linked(self, client: Client, admin_user: User, user_with_person: User) -> None:
        assert user_with_person.person

        # Act
        resp = client.get(self._get_url(user_with_person.person.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"link_token": None}
