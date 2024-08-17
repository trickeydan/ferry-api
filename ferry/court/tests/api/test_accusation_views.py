from http import HTTPStatus
from typing import Any
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import User
from ferry.api_legacy.tests.utils import APITest
from ferry.court.factories import AccusationFactory, PersonFactory
from ferry.court.models import Accusation, Person, Ratification


@pytest.mark.django_db
class TestAccusationListEndpoint(APITest):
    url = reverse_lazy("api-2.0.0:accusations-list")

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self.url)
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_no_results(self, client: Client, admin_user: User) -> None:
        resp = client.get(self.url, headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"count": 0, "next": None, "previous": None, "results": []}

    def test_get(self, client: Client, admin_user: User) -> None:
        # Arrange
        expected_ids = [str(AccusationFactory().id) for _ in range(10)]

        # Act
        resp = client.get(self.url, headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()

        assert data.keys() == {"count", "next", "previous", "results"}
        assert data["count"] == 10
        assert len(data["results"]) == 10
        actual_results = [item["id"] for item in data["results"]]
        assert sorted(actual_results) == sorted(expected_ids)


@pytest.mark.django_db
class TestAccusationCreateEndpoint(APITest):
    def _get_url(self) -> str:
        return reverse_lazy("api-2.0.0:accusations-list")

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url())
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                {
                    "quote": ["This field is required."],
                    "suspect": ["This field is required."],
                    "created_by": ["You must specify a person if no person is associated with your user."],
                },
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                {
                    "quote": ["This field is required."],
                    "suspect": ["This field is required."],
                    "created_by": ["You must specify a person if no person is associated with your user."],
                },
                id="spurious",
            ),
            pytest.param(
                {"quote": "bees", "created_by": str(UUID(int=0))},
                {
                    "suspect": ["This field is required."],
                    "created_by": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.'],
                },
                id="missing_suspect",
            ),
            pytest.param(
                {"quote": "bees", "suspect": str(UUID(int=0))},
                {
                    "suspect": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.'],
                    "created_by": ["You must specify a person if no person is associated with your user."],
                },
                id="missing_created_by",
            ),
            pytest.param(
                {"created_by": str(UUID(int=0)), "suspect": str(UUID(int=0))},
                {
                    "quote": ["This field is required."],
                    "suspect": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.'],
                    "created_by": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.'],
                },
                id="missing_quote",
            ),
            pytest.param(
                {"quote": 1234, "suspect": "a string", "created_by": 12},
                {
                    "suspect": ["“a string” is not a valid UUID."],
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
            data={"quote": "bees", "suspect": UUID(int=1), "created_by": UUID(int=0)},
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {
            "suspect": ['Invalid pk "00000000-0000-0000-0000-000000000001" - object does not exist.'],
            "created_by": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.'],
        }

    def test_post_empty_quote(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        suspect = PersonFactory()
        created_by = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"quote": "", "suspect": suspect.id, "created_by": created_by.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"quote": ["This field may not be blank."]}

    def test_post_suspect_is_creator(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"quote": "bees", "suspect": person.id, "created_by": person.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"non_field_errors": ["Unable to create accusation that suspects the creator."]}

    def test_post_not_permitted_to_create(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        suspect = PersonFactory()
        creator = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"quote": "bees", "suspect": suspect.id, "created_by": creator.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You cannot act on behalf of other people."}

    def _assert_response(self, resp: Any, user: User, suspect: Person, created_by: Person) -> None:
        # Assert
        assert resp.status_code == HTTPStatus.CREATED
        data = resp.json()
        assert data["quote"] == "bees"
        assert data["created_by"] == str(created_by.id)
        assert data["suspect"] == str(suspect.id)
        assert "ratification" not in data

        accusation = Accusation.objects.get(id=data["id"])
        assert accusation.quote == "bees"
        assert accusation.suspect_id == suspect.id
        assert accusation.created_by_id == created_by.id
        with pytest.raises(Ratification.DoesNotExist):
            _ = accusation.ratification

    def test_post_admin(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        suspect = PersonFactory()
        created_by = PersonFactory()
        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"quote": "bees", "suspect": suspect.id, "created_by": created_by.id},
        )
        self._assert_response(resp, admin_user, suspect, created_by)

    def test_post(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        assert user_with_person.person is not None
        suspect = PersonFactory()
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"quote": "bees", "suspect": suspect.id, "created_by": user_with_person.person.id},
        )
        self._assert_response(resp, user_with_person, suspect, user_with_person.person)

    def test_post__no_creator(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        assert user_with_person.person is not None
        suspect = PersonFactory()
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"quote": "bees", "suspect": suspect.id},
        )
        self._assert_response(resp, user_with_person, suspect, user_with_person.person)


@pytest.mark.django_db
class TestAccusationDetailEndpoint(APITest):
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:accusations-detail", args=[accusation_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, admin_user: User) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get_unratified(self, client: Client, admin_user: User) -> None:
        # Arrange
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.get(self._get_url(accusation.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data.keys() == {"id", "quote", "suspect", "created_by", "created_at", "updated_at", "ratification"}
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

    def test_get_ratified(self, client: Client, admin_user: User) -> None:
        # Arrange
        accusation = AccusationFactory()

        # Act
        resp = client.get(self._get_url(accusation.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data.keys() == {"id", "quote", "suspect", "created_by", "created_at", "updated_at", "ratification"}
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


@pytest.mark.django_db
class TestAccusationUpdateEndpoint(APITest):
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:accusations-detail", args=[accusation_id])

    def test_put_unauthenticated(self, client: Client) -> None:
        resp = client.put(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_put_404(self, client: Client, admin_user: User) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_put_no_payload(self, client: Client, admin_user: User) -> None:
        # Arrange
        accusation = AccusationFactory()

        # Act
        resp = client.put(self._get_url(accusation.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"quote": ["This field is required."]}

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                {"quote": ["This field is required."]},
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                {"quote": ["This field is required."]},
                id="spurious",
            ),
            pytest.param(
                {},
                {"quote": ["This field is required."]},
                id="missing_quote",
            ),
            pytest.param(
                {"quote": ""},
                {"quote": ["This field may not be blank."]},
                id="empty_quote",
            ),
        ],
    )
    def test_put_bad_payload(
        self, client: Client, admin_user: User, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Arrange
        accusation = AccusationFactory()

        # Act
        resp = client.put(
            self._get_url(accusation.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == errors

    def test_put(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        accusation = AccusationFactory(quote="bees")

        # Act
        resp = client.put(
            self._get_url(accusation.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"quote": "wasps"},
        )

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["id"] == str(accusation.id)
        assert data["quote"] == "wasps"

        accusation.refresh_from_db()
        assert accusation.quote == "wasps"


@pytest.mark.django_db
class TestAccusationDeleteEndpoint(APITest):
    def _get_url(self, person_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:accusations-detail", args=[person_id])

    def test_delete_unauthenticated(self, client: Client) -> None:
        resp = client.delete(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_404(self, client: Client, admin_user: User) -> None:
        resp = client.delete(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_delete_not_allowed(self, client: Client, user_with_person: User) -> None:
        accusation = AccusationFactory()

        # Act
        resp = client.delete(self._get_url(accusation.id), headers=self.get_headers(user_with_person))
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You do not have permission to perform this action."}

    def test_delete(self, client: Client, admin_user: User) -> None:
        # Arrange
        accusation = AccusationFactory()
        accusation_id = accusation.id

        # Act
        resp = client.delete(self._get_url(accusation.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.NO_CONTENT
        assert resp.content == b""

        assert not Accusation.objects.filter(id=accusation_id).exists()
