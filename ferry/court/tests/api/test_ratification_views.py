from http import HTTPStatus
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import APIToken
from ferry.court.factories import AccusationFactory, ConsequenceFactory, PersonFactory
from ferry.court.models import Ratification


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


@pytest.mark.django_db
class TestRatificationCreateEndpoint:
    def _get_headers(self, api_token: APIToken) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:ratification_create", args=[accusation_id])

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                [
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                [
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="spurious",
            ),
            pytest.param(
                {"quote": "bees", "suspect": str(UUID(int=0))},
                [
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="missing_created_by",
            ),
            pytest.param(
                {"created_by": 12},
                [
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
        self, client: Client, api_token: APIToken, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Arrange
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self._get_headers(api_token),
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
        api_token: APIToken,
    ) -> None:
        accusation = AccusationFactory(ratification=None)
        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"created_by": UUID(int=0)},
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
            ],
        }

    def test_post_ratifier_is_suspect(
        self,
        client: Client,
        api_token: APIToken,
    ) -> None:
        # Arrange
        ConsequenceFactory()
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"created_by": accusation.suspect.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [
                {"loc": "__all__", "detail": ["You cannot ratify an accusation made against you."]},
            ],
        }

    def test_post_ratifier_is_accuser(
        self,
        client: Client,
        api_token: APIToken,
    ) -> None:
        # Arrange
        ConsequenceFactory()
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"created_by": accusation.created_by.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [
                {"loc": "__all__", "detail": ["You cannot ratify an accusation that you made."]},
            ],
        }

    def test_post_no_consequences(
        self,
        client: Client,
        api_token: APIToken,
    ) -> None:
        # Arrange
        accusation = AccusationFactory(ratification=None)
        ratifier = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"created_by": ratifier.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        data = resp.json()
        assert data == {
            "detail": "No consequences available to assign",
            "status": "error",
            "status_code": 500,
            "status_name": "INTERNAL_SERVER_ERROR",
        }

    def test_post_already_ratified(
        self,
        client: Client,
        api_token: APIToken,
    ) -> None:
        # Arrange
        ConsequenceFactory()
        accusation = AccusationFactory()
        ratifier = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"created_by": ratifier.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.CONFLICT
        data = resp.json()
        assert data == {
            "detail": "Ratification already exists",
            "status": "error",
            "status_code": 409,
            "status_name": "CONFLICT",
        }

    def test_post(
        self,
        client: Client,
        api_token: APIToken,
    ) -> None:
        # Arrange
        consequences = ConsequenceFactory.create_batch(size=10)
        accusation = AccusationFactory(ratification=None)
        ratifier = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"created_by": ratifier.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["created_by"] == {
            "id": str(ratifier.id),
            "display_name": ratifier.display_name,
        }
        assert data["consequence"]["id"] is not None
        assert data["consequence"]["content"] is not None

        ratification = Ratification.objects.get(id=data["id"])
        assert ratification.created_by_id == ratifier.id
        assert ratification.accusation == accusation
        assert ratification.consequence in consequences
