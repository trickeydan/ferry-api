from http import HTTPStatus
from uuid import UUID

import pytest
from django.test import Client
from django.urls import reverse_lazy

from ferry.accounts.models import User
from ferry.conftest import APITest
from ferry.court.factories import AccusationFactory, ConsequenceFactory, PersonFactory
from ferry.court.models import Accusation, Person, Ratification


@pytest.mark.django_db
class TestRatificationDetailEndpoint(APITest):
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:accusations-ratification", args=[accusation_id])

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
        assert resp.status_code == HTTPStatus.NOT_FOUND
        data = resp.json()
        assert data == {"detail": "Accusation is not ratified."}

    def test_get(self, client: Client, admin_user: User) -> None:
        # Arrange
        accusation = AccusationFactory()

        # Act
        resp = client.get(self._get_url(accusation.id), headers=self.get_headers(admin_user))

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
class TestRatificationCreateEndpoint(APITest):
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:accusations-ratification", args=[accusation_id])

    def test_post_unauthenticated(self, client: Client) -> None:
        resp = client.post(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.parametrize(
        ("payload", "errors"),
        [
            pytest.param(
                {"created_by": 12},
                {"created_by": ['Invalid pk "12" - object does not exist.']},
                id="bad_types",
            ),
        ],
    )
    def test_post_bad_payload(
        self, client: Client, admin_user: User, payload: dict[str, int], errors: list[dict]
    ) -> None:
        # Arrange
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
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
        accusation = AccusationFactory(ratification=None)
        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"created_by": UUID(int=0)},
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"created_by": ['Invalid pk "00000000-0000-0000-0000-000000000000" - object does not exist.']}

    def test_post_ratifier_is_suspect(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        ConsequenceFactory()
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"created_by": accusation.suspect.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"created_by": ["You cannot ratify an accusation made against you."]}

    def test_post_ratifier_is_accuser(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        ConsequenceFactory()
        accusation = AccusationFactory(ratification=None)

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"created_by": accusation.created_by.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.BAD_REQUEST
        data = resp.json()
        assert data == {"created_by": ["You cannot ratify an accusation that you made."]}

    def test_post_no_consequences(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        accusation = AccusationFactory(ratification=None)
        ratifier = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"created_by": ratifier.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.NOT_ACCEPTABLE
        data = resp.json()
        assert data == {"detail": "No consequences available to assign"}

    def test_post_already_ratified(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        # Arrange
        ConsequenceFactory()
        accusation = AccusationFactory()
        ratifier = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self.get_headers(admin_user),
            content_type="application/json",
            data={"created_by": ratifier.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.CONFLICT
        data = resp.json()
        assert data == {"detail": "Accusation is already ratified."}

    def test_post_no_permission(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        # Arrange
        ConsequenceFactory()
        accusation = AccusationFactory(ratification=None)
        ratifier = PersonFactory()

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self.get_headers(user_with_person),
            content_type="application/json",
            data={"created_by": ratifier.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You cannot act on behalf of other people."}

    def _test_post(
        self,
        client: Client,
        user: User,
        accusation: Accusation,
        ratifier: Person,
    ) -> None:
        consequences = ConsequenceFactory.create_batch(size=10)

        # Act
        resp = client.post(
            self._get_url(accusation_id=accusation.id),
            headers=self.get_headers(user),
            content_type="application/json",
            data={"created_by": ratifier.id},
        )

        # Assert
        assert resp.status_code == HTTPStatus.CREATED
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

    def test_post_admin(
        self,
        client: Client,
        admin_user: User,
    ) -> None:
        accusation = AccusationFactory(ratification=None)
        ratifier = PersonFactory()

        self._test_post(client, admin_user, accusation, ratifier)

    def test_post(
        self,
        client: Client,
        user_with_person: User,
    ) -> None:
        assert user_with_person.person is not None
        accusation = AccusationFactory(ratification=None)
        ratifier = user_with_person.person
        self._test_post(client, user_with_person, accusation, ratifier)


@pytest.mark.django_db
class TestRatificationDeleteEndpoint(APITest):
    def _get_url(self, accusation_id: UUID) -> str:
        return reverse_lazy("api-2.0.0:accusations-ratification", args=[accusation_id])

    def test_delete_unauthenticated(self, client: Client) -> None:
        resp = client.delete(self._get_url(UUID(int=0)))
        assert resp.status_code == HTTPStatus.UNAUTHORIZED

    def test_delete_404(self, client: Client, admin_user: User) -> None:
        resp = client.delete(self._get_url(UUID(int=0)), headers=self.get_headers(admin_user))
        assert resp.status_code == HTTPStatus.NOT_FOUND

    def test_delete_no_permission(self, client: Client, user_with_person: User) -> None:
        # Arrange
        accusation = AccusationFactory()

        # Act
        resp = client.delete(self._get_url(accusation.id), headers=self.get_headers(user_with_person))

        # Assert
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {"detail": "You do not have permission to perform this action."}

    def test_delete(self, client: Client, admin_user: User) -> None:
        # Arrange
        accusation = AccusationFactory()
        accusation_id = accusation.id

        # Sanity check
        assert Ratification.objects.filter(accusation_id=accusation_id).exists()

        # Act
        resp = client.delete(self._get_url(accusation.id), headers=self.get_headers(admin_user))

        # Assert
        assert resp.status_code == HTTPStatus.NO_CONTENT
        assert resp.content == b""

        assert Accusation.objects.filter(id=accusation_id).exists()
        assert not Ratification.objects.filter(accusation_id=accusation_id).exists()
