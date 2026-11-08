from datetime import timedelta
from http import HTTPStatus
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ferry.accounts.models import Person, User
from ferry.conftest import APITest
from ferry.pub.models import Pub, PubEvent, PubEventAttendanceTombstone, PubEventRSVP, PubEventRSVPMethod
from ferry.pub.services import TombstoneAlreadyExistsError, set_autopub, skip_next_pub, undo_skip_next_pub

type _Response = Any

HTMX = {"HX-Request": "true"}
HTMX_ON_OVERVIEW = {"HX-Request": "true", "HX-Current-URL": "http://testserver/pub/"}


def create_event(person: Person) -> PubEvent:
    pub, _ = Pub.objects.get_or_create(
        name="The Anchor", defaults={"emoji": "🍺", "map_url": "https://example.com/map"}
    )
    return PubEvent.objects.create(timestamp=timezone.now() + timedelta(days=2), pub=pub, created_by=person)


def rsvp(event: PubEvent, person: Person, method: str, *, attending: bool = True) -> PubEventRSVP:
    return PubEventRSVP.objects.create(pub_event=event, person=person, is_attending=attending, method=method)


@pytest.fixture
def autopub_person(person: Person) -> Person:
    person.autopub = True
    person.save()
    return person


@pytest.mark.django_db
class TestSkipService:
    def test_skip_before_next_pub_exists(self, autopub_person: Person) -> None:
        tombstone = skip_next_pub(autopub_person)

        assert tombstone.pub_event is None

    def test_skip_when_next_pub_exists_links_and_updates_rsvp(self, autopub_person: Person) -> None:
        event = create_event(autopub_person)
        auto = rsvp(event, autopub_person, PubEventRSVPMethod.AUTO)

        tombstone = skip_next_pub(autopub_person)

        auto.refresh_from_db()
        assert tombstone.pub_event == event
        assert auto.method == PubEventRSVPMethod.TOMBSTONE
        assert not auto.is_attending

    def test_skip_twice_fails(self, autopub_person: Person) -> None:
        skip_next_pub(autopub_person)

        with pytest.raises(TombstoneAlreadyExistsError):
            skip_next_pub(autopub_person)

    def test_undo_before_next_pub_exists(self, autopub_person: Person) -> None:
        skip_next_pub(autopub_person)

        assert undo_skip_next_pub(autopub_person)
        assert not PubEventAttendanceTombstone.objects.exists()

    def test_undo_without_skip(self, autopub_person: Person) -> None:
        assert not undo_skip_next_pub(autopub_person)

    def test_undo_restores_autopub_rsvp(self, autopub_person: Person) -> None:
        event = create_event(autopub_person)
        auto = rsvp(event, autopub_person, PubEventRSVPMethod.AUTO)
        skip_next_pub(autopub_person)

        undo_skip_next_pub(autopub_person)

        auto.refresh_from_db()
        assert auto.method == PubEventRSVPMethod.AUTO
        assert auto.is_attending
        assert not PubEventAttendanceTombstone.objects.exists()

    def test_turning_autopub_off_clears_pending_skip_only(self, autopub_person: Person) -> None:
        event = create_event(autopub_person)
        linked = PubEventAttendanceTombstone.objects.create(person=autopub_person, pub_event=event)
        PubEventAttendanceTombstone.objects.create(person=autopub_person, pub_event=None)

        set_autopub(autopub_person, enabled=False)

        autopub_person.refresh_from_db()
        assert not autopub_person.autopub
        assert list(PubEventAttendanceTombstone.objects.all()) == [linked]


@pytest.mark.django_db
class TestSkipViews:
    skip_url = reverse("pub:skip-next")
    undo_url = reverse("pub:undo-skip-next")

    def test_requires_htmx(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        client.force_login(user_with_person)

        assert client.post(self.skip_url).status_code == HTTPStatus.BAD_REQUEST

    def test_requires_autopub(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.post(self.skip_url, headers=HTMX)

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not PubEventAttendanceTombstone.objects.exists()

    def test_skip_before_pub_chosen(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        client.force_login(user_with_person)

        response = client.post(self.skip_url, headers=HTMX)

        assert response.status_code == HTTPStatus.OK
        assert PubEventAttendanceTombstone.objects.filter(person=autopub_person, pub_event=None).exists()
        assert b"You've skipped the next pub" in response.content
        assert b"Undo skip" in response.content

    def test_skip_is_idempotent(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        client.force_login(user_with_person)

        client.post(self.skip_url, headers=HTMX)
        response = client.post(self.skip_url, headers=HTMX)

        assert response.status_code == HTTPStatus.OK
        assert PubEventAttendanceTombstone.objects.count() == 1

    def test_skip_with_pub_chosen(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        event = create_event(autopub_person)
        auto = rsvp(event, autopub_person, PubEventRSVPMethod.AUTO)
        client.force_login(user_with_person)

        response = client.post(self.skip_url, headers=HTMX)

        auto.refresh_from_db()
        assert auto.method == PubEventRSVPMethod.TOMBSTONE
        assert b"You skipped this one" in response.content

    def test_undo_skip(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        skip_next_pub(autopub_person)
        client.force_login(user_with_person)

        response = client.post(self.undo_url, headers=HTMX)

        assert response.status_code == HTTPStatus.OK
        assert not PubEventAttendanceTombstone.objects.exists()
        assert b"Skip next pub" in response.content

    def test_autopub_card_only_swapped_in_on_pub_overview(
        self, client: Client, user_with_person: User, autopub_person: Person
    ) -> None:
        client.force_login(user_with_person)

        home = client.post(self.skip_url, headers=HTMX)
        client.post(self.undo_url, headers=HTMX)
        overview = client.post(self.skip_url, headers=HTMX_ON_OVERVIEW)

        assert b'id="autopub-card"' not in home.content
        assert b'id="autopub-card"' in overview.content
        assert b'hx-swap-oob="true"' in overview.content


@pytest.mark.django_db
class TestSkipButtonVisibility:
    url = reverse("dashboard:home")

    def get(self, client: Client, user: User) -> str:
        client.force_login(user)
        return client.get(self.url).content.decode()

    def test_hidden_without_autopub(self, client: Client, user_with_person: User) -> None:
        content = self.get(client, user_with_person)

        assert "Skip next pub" not in content
        assert "Undo skip" not in content

    def test_shown_before_pub_chosen(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        assert "Skip next pub" in self.get(client, user_with_person)

    def test_shown_when_autopub_rsvp_exists(
        self, client: Client, user_with_person: User, autopub_person: Person
    ) -> None:
        rsvp(create_event(autopub_person), autopub_person, PubEventRSVPMethod.AUTO)

        assert "Skip next pub" in self.get(client, user_with_person)

    def test_hidden_when_rsvp_is_not_autopub(
        self, client: Client, user_with_person: User, autopub_person: Person
    ) -> None:
        rsvp(create_event(autopub_person), autopub_person, PubEventRSVPMethod.WEB)

        content = self.get(client, user_with_person)

        assert "Skip next pub" not in content
        assert "Undo skip" not in content

    def test_undo_shown_when_skipped(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        rsvp(create_event(autopub_person), autopub_person, PubEventRSVPMethod.TOMBSTONE, attending=False)

        assert "Undo skip" in self.get(client, user_with_person)


@pytest.mark.django_db
class TestAutoPubView:
    url = reverse("pub:autopub")

    def test_turn_on(self, client: Client, user_with_person: User, person: Person) -> None:
        client.force_login(user_with_person)

        response = client.post(self.url, {"enabled": "1"}, headers=HTMX_ON_OVERVIEW)

        person.refresh_from_db()
        assert response.status_code == HTTPStatus.OK
        assert person.autopub
        assert b"Turn off AutoPub" in response.content
        assert b'id="next-pub-card"' in response.content

    def test_turn_off_clears_pending_skip(self, client: Client, user_with_person: User, autopub_person: Person) -> None:
        skip_next_pub(autopub_person)
        client.force_login(user_with_person)

        response = client.post(self.url, {"enabled": "0"}, headers=HTMX_ON_OVERVIEW)

        autopub_person.refresh_from_db()
        assert not autopub_person.autopub
        assert not PubEventAttendanceTombstone.objects.exists()
        assert b"Turn on AutoPub" in response.content

    def test_rejects_bad_value(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        assert client.post(self.url, {"enabled": "maybe"}, headers=HTMX).status_code == HTTPStatus.BAD_REQUEST

    def test_requires_htmx(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        assert client.post(self.url, {"enabled": "1"}).status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
class TestEventPageAfterSkipping:
    def test_coming_after_skipping_is_an_explicit_yes(
        self, client: Client, user_with_person: User, autopub_person: Person
    ) -> None:
        event = create_event(autopub_person)
        rsvp(event, autopub_person, PubEventRSVPMethod.AUTO)
        skip_next_pub(autopub_person)
        client.force_login(user_with_person)

        response = client.post(reverse("pub:events-update-response", args=[event.id]), headers=HTMX)

        updated = PubEventRSVP.objects.get(pub_event=event, person=autopub_person)
        assert response.status_code == HTTPStatus.OK
        assert updated.method == PubEventRSVPMethod.WEB
        assert updated.is_attending
        assert not PubEventAttendanceTombstone.objects.exists()


@pytest.mark.django_db
class TestTombstoneApi(APITest):
    url = reverse("api-2.0.0:events-create-tombstone")

    def post(self, client: Client, headers: dict[str, str], person: Person) -> _Response:
        return client.post(
            self.url,
            headers=headers,
            content_type="application/json",
            data={"person": str(person.id)},
        )

    def test_create_links_to_next_event(self, client: Client, admin_user: User, autopub_person: Person) -> None:
        event = create_event(autopub_person)
        auto = rsvp(event, autopub_person, PubEventRSVPMethod.AUTO)

        response = self.post(client, self.get_headers(admin_user), autopub_person)

        auto.refresh_from_db()
        assert response.status_code == HTTPStatus.OK
        assert response.json()["pub_event"] == str(event.id)
        assert auto.method == PubEventRSVPMethod.TOMBSTONE

    def test_duplicate_conflicts(self, client: Client, admin_user: User, autopub_person: Person) -> None:
        headers = self.get_headers(admin_user)
        self.post(client, headers, autopub_person)

        response = self.post(client, headers, autopub_person)

        assert response.status_code == HTTPStatus.CONFLICT

    def test_requires_autopub(self, client: Client, admin_user: User, person: Person) -> None:
        response = self.post(client, self.get_headers(admin_user), person)

        assert response.status_code == HTTPStatus.BAD_REQUEST
