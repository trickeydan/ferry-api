from http import HTTPStatus
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import APIToken
from ferry.court.factories import ConsequenceFactory, PersonFactory
from ferry.court.models import Consequence


@pytest.mark.django_db
class TestConsequenceListEndpoint:
    url = reverse_lazy("api-1.0.0:consequence_list")

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
        expected_ids = [str(ConsequenceFactory().id) for _ in range(10)]

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
class TestConsequenceCreateEndpoint:
    def _get_headers(self, api_token: APIToken) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get_url(self) -> str:
        return reverse_lazy("api-1.0.0:consequence_create")

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url())
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {},
                [
                    {"type": "missing", "loc": ["body", "payload", "content"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                [
                    {"type": "missing", "loc": ["body", "payload", "content"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="spurious",
            ),
            pytest.param(
                {"is_enabled": True, "created_by": str(UUID(int=0))},
                [
                    {"type": "missing", "loc": ["body", "payload", "content"], "msg": "Field required"},
                ],
                id="missing_content",
            ),
            pytest.param(
                {"content": "bees", "is_enabled": True},
                [
                    {"type": "missing", "loc": ["body", "payload", "created_by"], "msg": "Field required"},
                ],
                id="missing_created_by",
            ),
            pytest.param(
                {"content": 1234, "is_enabled": "a string", "created_by": 12},
                [
                    {
                        "type": "string_type",
                        "loc": ["body", "payload", "content"],
                        "msg": "Input should be a valid string",
                    },
                    {
                        "type": "bool_parsing",
                        "loc": ["body", "payload", "is_enabled"],
                        "msg": "Input should be a valid boolean, unable to interpret input",
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
        self, client: Client, api_token: APIToken, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Act
        resp = client.post(
            self._get_url(),
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
        # Act
        resp = client.post(
            self._get_url(),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"content": "bees", "is_enabled": False, "created_by": UUID(int=0)},
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 422,
            "status_name": "UNPROCESSABLE_ENTITY",
            "detail": [
                {"loc": "created_by", "detail": "Unable to find person with ID 00000000-0000-0000-0000-000000000000"}
            ],
        }

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
        api_token: APIToken,
        payload: dict,
        expected_content: str,
        expected_is_enabled: bool,  # noqa: FBT001
    ) -> None:
        # Arrange
        person = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data={"created_by": person.id, **payload},
        )

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data["content"] == expected_content
        assert data["is_enabled"] == expected_is_enabled
        assert data["created_by"] == {
            "id": str(person.id),
            "display_name": person.display_name,
        }

        consequence = Consequence.objects.get(id=data["id"])
        assert consequence.content == expected_content
        assert consequence.is_enabled == expected_is_enabled
        assert consequence.created_by_id == person.id


@pytest.mark.django_db
class TestConsequenceDetailEndpoint:
    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:consequence_detail", args=[consequence_id])

    def test_get_unauthenticated(self, client: Client) -> None:
        resp = client.get(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_get_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers={"Authorization": f"Bearer {api_token.token}"})
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_get(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        consequence = ConsequenceFactory()

        # Act
        resp = client.get(self._get_url(consequence.id), headers={"Authorization": f"Bearer {api_token.token}"})

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


@pytest.mark.django_db
class TestConsequenceUpdateEndpoint:
    def _get_headers(self, api_token: APIToken) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:consequence_update", args=[consequence_id])

    def test_put_unauthenticated(self, client: Client) -> None:
        resp = client.put(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_put_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.get(self._get_url(UUID(int=0)), headers=self._get_headers(api_token))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_put_no_payload(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        consequence = ConsequenceFactory()

        # Act
        resp = client.put(self._get_url(consequence.id), headers=self._get_headers(api_token))

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
                    {"type": "missing", "loc": ["body", "payload", "content"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "is_enabled"], "msg": "Field required"},
                ],
                id="empty-dict",
            ),
            pytest.param(
                {"bees": 4},
                [
                    {"type": "missing", "loc": ["body", "payload", "content"], "msg": "Field required"},
                    {"type": "missing", "loc": ["body", "payload", "is_enabled"], "msg": "Field required"},
                ],
                id="spurious",
            ),
            pytest.param(
                {"is_enabled": True},
                [
                    {"type": "missing", "loc": ["body", "payload", "content"], "msg": "Field required"},
                ],
                id="missing_content",
            ),
            pytest.param(
                {"content": "bees"},
                [
                    {"type": "missing", "loc": ["body", "payload", "is_enabled"], "msg": "Field required"},
                ],
                id="missing_is_enabled",
            ),
            pytest.param(
                {"content": 1234, "is_enabled": "a string"},
                [
                    {
                        "type": "string_type",
                        "loc": ["body", "payload", "content"],
                        "msg": "Input should be a valid string",
                    },
                    {
                        "type": "bool_parsing",
                        "loc": ["body", "payload", "is_enabled"],
                        "msg": "Input should be a valid boolean, unable to interpret input",
                    },
                ],
                id="bad_types",
            ),
        ],
    )
    def test_put_bad_payload(
        self, client: Client, api_token: APIToken, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Arrange
        consequence = ConsequenceFactory()

        # Act
        resp = client.put(
            self._get_url(consequence.id),
            headers=self._get_headers(api_token),
            content_type="application/json",
            data=payload,
        )

        # Assert
        assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        data = resp.json()
        assert data == {"status": "error", "status_code": 422, "status_name": "UNPROCESSABLE_ENTITY", "detail": errors}

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
        api_token: APIToken,
        payload: dict,
        expected_content: str,
        expected_is_enabled: bool,  # noqa: FBT001
    ) -> None:
        # Arrange
        consequence = ConsequenceFactory(content="not bees", is_enabled=not expected_is_enabled)

        # Act
        resp = client.put(
            self._get_url(consequence.id),
            headers=self._get_headers(api_token),
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
class TestConsequencesDeleteEndpoint:
    def _get_headers(self, api_token: APIToken) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get_url(self, consequence_id: UUID) -> str:
        return reverse_lazy("api-1.0.0:consequence_delete", args=[consequence_id])

    def test_delete_unauthenticated(self, client: Client) -> None:
        resp = client.delete(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_404(self, client: Client, api_token: APIToken) -> None:
        resp = client.delete(self._get_url(UUID(int=0)), headers=self._get_headers(api_token))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_delete(self, client: Client, api_token: APIToken) -> None:
        # Arrange
        consequence = ConsequenceFactory()
        consequence_id = consequence.id

        # Act
        resp = client.delete(self._get_url(consequence.id), headers=self._get_headers(api_token))

        # Assert
        assert resp.status_code == HTTPStatus.OK
        data = resp.json()
        assert data == {"status": "success"}

        assert not Consequence.objects.filter(id=consequence_id).exists()
