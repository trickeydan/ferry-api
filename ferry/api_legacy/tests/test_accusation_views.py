from http import HTTPStatus
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
    url = reverse_lazy("api-1.0.0:accusation_list")

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
        expected_ids = [str(AccusationFactory().id) for _ in range(10)]

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
class TestAccusationCreateEndpoint(APITest):
    def _get_url(self) -> str:
        return reverse_lazy("api-1.0.0:accusation_create")

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url())
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                [
                    {"type": "missing", "loc": ["body", "payload", "quote"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "suspect"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                [
                    {"type": "missing", "loc": ["body", "payload", "quote"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "suspect"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="spurious",
            ),
            pytest.param(
                {"quote": "bees", "created_by": str(UUID(int=0))},
                [
                    {"type": "missing", "loc": ["body", "payload", "suspect"], "msg": "Field required"},
                ],
                id="missing_suspect",
            ),
            pytest.param(
                {"quote": "bees", "suspect": str(UUID(int=0))},
                [
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="missing_created_by",
            ),
            pytest.param(
                {"created_by": str(UUID(int=0)), "suspect": str(UUID(int=0))},
                [
                    {"type": "missing", "loc": ["body", "payload", "quote"], "msg": "Field required"},
                ],
                id="missing_quote",
            ),
            pytest.param(
                {"quote": 1234, "suspect": "a string", "created_by": 12},
                [
                    {
                        "type": "string_type",
                        "loc": ["body", "payload", "quote"],
                        "msg": "Input should be a valid string",
                    },
                    {
                        "type": "uuid_parsing",
                        "loc": ["body", "payload", "suspect"],
                        "msg": "Input should be a valid UUID, invalid character: expected an optional prefix of `urn:uuid:` followed by [0-9a-fA-F-], found ` ` at 2",  # noqa: E501
                        "ctx": {
                            "error": "invalid character: expected an optional prefix of `urn:uuid:` followed by [0-9a-fA-F-], found ` ` at 2"  # noqa: E501
                        },
                    },
                    {
                        "type": "uuid_type",
                        "loc": ["body", "payload", "created_by"],
                        "msg": "UUID input should be a string, bytes or UUID object",
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
        assert data == {"status": "error", "status_code": 422, "status_name": "UNPROCESSABLE_ENTITY", "detail": errors}

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
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [
                {"loc": "created_by", "detail": "Unable to find person with ID 00000000-0000-0000-0000-000000000000"},
                {"loc": "suspect", "detail": "Unable to find person with ID 00000000-0000-0000-0000-000000000001"},
            ],
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
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [
                {"loc": "quote", "detail": ["This field cannot be blank."]},
            ],
        }

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
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [
                {"loc": "__all__", "detail": "Unable to create accusation that suspects the creator."},
            ],
        }

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
        assert data == {
            "status": "error",
            "status_code": 403,
            "status_name": "FORBIDDEN",
            "detail": "You cannot act on behalf of other people.",
        }

    def _test_post(self, client: Client, user: User, suspect: Person, created_by: Person) -> None:
        # Act
        resp = client.post(
            self._get_url(),
            headers=self.get_headers(user),
            content_type="application/json",
            data={"quote": "bees", "suspect": suspect.id, "created_by": created_by.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["quote"] == "bees"
        assert data["created_by"] == {
            "id": str(created_by.id),
            "display_name": created_by.display_name,
        }
        assert data["suspect"] == {
            "id": str(suspect.id),
            "display_name": suspect.display_name,
        }
        assert data["ratification"] is None

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
        self._test_post(client, admin_user, suspect, created_by)

    def test_post(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        assert user_with_person.person is not None
        suspect = PersonFactory()
        self._test_post(client, user_with_person, suspect, user_with_person.person)


@pytest.mark.django_db
class TestAccusationDetailEndpoint(APITest):
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:accusation_detail", args=[accusation_id])

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
        return reverse_lazy("api-1.0.0:accusation_update", args=[accusation_id])

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
                    {"type": "missing", "loc": ["body", "payload", "quote"], "msg": "Field required"},
                ],
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                [
                    {"type": "missing", "loc": ["body", "payload", "quote"], "msg": "Field required"},
                ],
                id="spurious",
            ),
            pytest.param(
                {},
                [
                    {"type": "missing", "loc": ["body", "payload", "quote"], "msg": "Field required"},
                ],
                id="missing_quote",
            ),
            pytest.param(
                {"quote": 1234},
                [
                    {
                        "type": "string_type",
                        "loc": ["body", "payload", "quote"],
                        "msg": "Input should be a valid string",
                    },
                ],
                id="bad_types",
            ),
            pytest.param(
                {"quote": ""},
                [
                    {
                        "loc": "quote",
                        "detail": ["This field cannot be blank."],
                    },
                ],
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
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {"status": "error", "status_code": 422, "status_name": "UNPROCESSABLE_ENTITY", "detail": errors}

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
        return reverse_lazy("api-1.0.0:accusation_delete", args=[person_id])

    def test_delete_unauthenticated(self, client: Client) -> None:
        resp = client.delete(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_404(self, client: Client, admin_user: User) -> None:
        resp = client.delete(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, client: Client, admin_user: User) -> None:
        # Arrange
        accusation = AccusationFactory()
        accusation_id = accusation.id

        # Act
        resp = client.delete(self._get_url(accusation.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"status": "success"}

        assert not Accusation.objects.filter(id=accusation_id).exists()
