from http import HTTPStatus
from typing import Any
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import Person, User
from ferry.conftest import APITest
from ferry.court.factories import ConsequenceFactory
from ferry.court.models import Consequence


@pytest.mark.django_db
class TestConsequenceListEndpoint(APITest):
    url = reverse_lazy("api-2.0.0:consequences-list")

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self.url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_no_results(self, client: Client, admin_user: User) -> None:
        # Act
        resp = client.get(self.url, headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"count": 0, "next": None, "previous": None, "results": []}

    def test_get_superuser(self, client: Client, admin_user: User) -> None:
        # Arrange
        expected_ids = [str(ConsequenceFactory().id) for _ in range(10)]  # not owned by user

        # Act
        resp = client.get(self.url, headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["count"] == 10
        assert len(data["results"]) == 10
        actual_results = [item["id"] for item in data["results"]]
        assert sorted(actual_results) == sorted(expected_ids)

    def test_get(self, client: Client, user_with_person: User) -> None:
        # Arrange
        expected_ids = [str(ConsequenceFactory(created_by=user_with_person.person).id) for _ in range(5)]

        ConsequenceFactory.create_batch(size=5)  # Expected to be excluded

        # Act
        resp = client.get(self.url, headers=self.get_headers(user_with_person))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data["count"] == 5
        assert len(data["results"]) == 5
        actual_results = [item["id"] for item in data["results"]]
        assert sorted(actual_results) == sorted(expected_ids)


@pytest.mark.django_db
class TestConsequenceCreateEndpoint(APITest):
    def _get_url(self) -> str:
        return reverse_lazy("api-2.0.0:consequences-list")

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url())
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                {
                    "content": ["This field is required."],
                    "created_by": ["You must specify a person if no person is associated with your user."],
                },
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                {
                    "content": ["This field is required."],
                    "created_by": ["You must specify a person if no person is associated with your user."],
                },
                id="spurious",
            ),
            pytest.param(
                {"is_enabled": True, "created_by": str(UUID(int=0))},
                {
                    "content": ["This field is required."],
                    "created_by": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.'],
                },
                id="missing_content",
            ),
            pytest.param(
                {"content": "bees", "is_enabled": True},
                {"created_by": ["You must specify a person if no person is associated with your user."]},
                id="missing_created_by",
            ),
            pytest.param(
                {"content": 1234, "is_enabled": "a string", "created_by": 12},
                {
                    "is_enabled": ["Must be a valid boolean."],
                    "created_by": ['Invalid pk "12" - object does not exist.'],
                },
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
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == errors

    def test_post_no_such_person(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"content": "bees", "is_enabled": False, "created_by": UUID(int=0)},
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"created_by": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.']}

    def test_post_cannot_act_on_behalf(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"content": "bees", "is_enabled": False, "created_by": person.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You cannot act on behalf of other people."}

    def _assert_post_response(
        self,
        resp: Any,
        person: Person,
        expected_content: str,
        expected_is_enabled: bool,  # noqa: FBT001
    ) -> None:
        # Assert
        assert resp.status_code == HTTPStatus.CREATED
        data = resp.json()
        assert data["content"] == expected_content
        assert data["is_enabled"] == expected_is_enabled
        assert data["created_by"] == str(person.id)

        consequence = Consequence.objects.get(id=data["id"])
        assert consequence.content == expected_content
        assert consequence.is_enabled == expected_is_enabled
        assert consequence.created_by_id == person.id

    @pytest.mark.parametrize(
        ("payload", "expected_content", "expected_is_enabled"),
        [
            pytest.param({"content": "bees", "is_enabled": False}, "bees", False, id="disabled"),
            pytest.param({"content": "wasps", "is_enabled": True}, "wasps", True, id="enabled"),
        ],
    )
    def test_post_superuser(
        self,
        client: Client,
        admin_user: User,
        payload: dict,
        expected_content: str,
        expected_is_enabled: bool,  # noqa: FBT001
    ) -> None:
        person = PersonFactory()

        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"created_by": str(person.id), **payload},
        )

        self._assert_post_response(resp, person, expected_content, expected_is_enabled)

    def test_post_superuser__no_person(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"content": "bees", "is_enabled": False},
        )

        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"created_by": ["You must specify a person if no person is associated with your user."]}

    @pytest.mark.parametrize(
        ("payload", "expected_content", "expected_is_enabled"),
        [
            pytest.param({"content": "bees", "is_enabled": False}, "bees", False, id="disabled"),
            pytest.param({"content": "wasps", "is_enabled": True}, "wasps", True, id="enabled"),
        ],
    )
    def test_post(
        self,
        client: Client,
        user_with_person: User,
        payload: dict,
        expected_content: str,
        expected_is_enabled: bool,  # noqa: FBT001
    ) -> None:
        person = user_with_person.person

        resp = client.post(
            self._get_url(),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data=payload,
        )

        self._assert_post_response(resp, person, expected_content, expected_is_enabled)


@pytest.mark.django_db
class TestConsequenceDetailEndpoint(APITest):
    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:consequences-detail", args=[consequence_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, admin_user: User) -> None:
        # Act
        resp = client.get(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get_no_permission(self, client: Client, user_with_person: Person) -> None:
        # Arrange
        consequence = ConsequenceFactory()

        # Act
        resp = client.get(self._get_url(consequence.id), headers=self.get_headers(user_with_person))

        # Assert
        assert resp.status_code == HTTPStatus.NOT_FOUND
        data = resp.json()
        assert data == {"detail": "No Consequence matches the given query."}

    def _test_get(self, client: Client, user: User, consequence: Consequence) -> None:
        resp = client.get(self._get_url(consequence.id), headers=self.get_headers(user))

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

    def test_get(self, client: Client, user_with_person: User) -> None:
        consequence = ConsequenceFactory(created_by=user_with_person.person)

        self._test_get(client, user_with_person, consequence)

    def test_get_admin(self, client: Client, admin_user: User) -> None:
        consequence = ConsequenceFactory()

        self._test_get(client, admin_user, consequence)


@pytest.mark.django_db
class TestConsequenceUpdateEndpoint(APITest):
    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:consequences-detail", args=[consequence_id])

    def test_put_unauthenticated(self, client: Client) -> None:
        resp = client.put(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_put_404(self, client: Client, admin_user: User) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_put_no_payload(self, client: Client, admin_user: User) -> None:
        # Arrange
        consequence = ConsequenceFactory()

        # Act
        resp = client.put(self._get_url(consequence.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"content": ["This field is required."]}

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                {"content": ["This field is required."]},
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                {"content": ["This field is required."]},
                id="spurious",
            ),
            pytest.param(
                {"is_enabled": True},
                {"content": ["This field is required."]},
                id="missing_content",
            ),
            pytest.param(
                {"content": 1234, "is_enabled": "a string"},
                {"is_enabled": ["Must be a valid boolean."]},
                id="bad_types",
            ),
        ],
    )
    def test_put_bad_payload(
        self, client: Client, admin_user: User, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Arrange
        consequence = ConsequenceFactory()

        # Act
        resp = client.put(
            self._get_url(consequence.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == errors

    def test_put_no_permission(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        # Arrange
        consequence = ConsequenceFactory(created_by=user_with_person.person)

        # Act
        resp = client.put(
            self._get_url(consequence.id),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"content": "bees", "is_enabled": False},
        )

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You do not have permission to perform this action."}

    @pytest.mark.parametrize(
        ("payload", "expected_content", "expected_is_enabled"),
        [
            pytest.param({"content": "bees", "is_enabled": False}, "bees", False, id="disabled"),
            pytest.param({"content": "wasps", "is_enabled": True}, "wasps", True, id="enabled"),
        ],
    )
    def test_put(
        self,
        client: Client,
        admin_user: User,
        payload: dict,
        expected_content: str,
        expected_is_enabled: bool,  # noqa: FBT001
    ) -> None:
        # Arrange
        consequence = ConsequenceFactory(content="not bees", is_enabled=not expected_is_enabled)

        # Act
        resp = client.put(
            self._get_url(consequence.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(consequence.id)
        assert data["content"] == expected_content
        assert data["is_enabled"] == expected_is_enabled

        consequence.refresh_from_db()
        assert consequence.content == expected_content
        assert consequence.is_enabled == expected_is_enabled


@pytest.mark.django_db
class TestConsequencesDeleteEndpoint(APITest):
    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:consequences-detail", args=[consequence_id])

    def test_delete_unauthenticated(self, client: Client) -> None:
        resp = client.delete(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_404(self, client: Client, admin_user: User) -> None:
        resp = client.delete(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_delete_no_permission(self, client: Client, user_with_person: User) -> None:
        # Arrange
        consequence = ConsequenceFactory(created_by=user_with_person.person)

        # Act
        resp = client.delete(self._get_url(consequence.id), headers=self.get_headers(user_with_person))

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You do not have permission to perform this action."}

    def test_delete(self, client: Client, admin_user: User) -> None:
        # Arrange
        consequence = ConsequenceFactory()
        consequence_id = consequence.id

        # Act
        resp = client.delete(self._get_url(consequence.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.NO_CONTENT
        assert resp.content == b""

        assert not Consequence.objects.filter(id=consequence_id).exists()
