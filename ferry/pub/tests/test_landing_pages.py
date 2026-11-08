from datetime import timedelta
from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ferry.accounts.models import Person, User
from ferry.court.factories import AccusationFactory, ConsequenceFactory
from ferry.pub.models import Pub, PubEvent, PubEventAttendanceTombstone, PubEventRSVP, PubEventRSVPMethod


def create_event(person: Person, *, days: int) -> PubEvent:
    pub, _ = Pub.objects.get_or_create(
        name="The Anchor", defaults={"emoji": "🍺", "map_url": "https://example.com/map"}
    )
    return PubEvent.objects.create(timestamp=timezone.now() + timedelta(days=days), pub=pub, created_by=person)


@pytest.mark.django_db
class TestNextEventCard:
    """The card is shared by the home page and the pub overview, so both are checked."""

    urls = (reverse("dashboard:home"), reverse("pub:overview"))

    @pytest.mark.parametrize("url", urls)
    def test_no_next_event(self, client: Client, user_with_person: User, url: str) -> None:
        client.force_login(user_with_person)

        response = client.get(url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["next_event"] is None
        assert b"Not chosen yet" in response.content

    @pytest.mark.parametrize("url", urls)
    def test_no_next_event_with_tombstone(
        self, client: Client, user_with_person: User, person: Person, url: str
    ) -> None:
        PubEventAttendanceTombstone.objects.create(person=person, pub_event=None)
        client.force_login(user_with_person)

        response = client.get(url)

        assert b"You've skipped the next pub" in response.content

    @pytest.mark.parametrize("url", urls)
    def test_no_next_event_with_autopub(self, client: Client, user_with_person: User, person: Person, url: str) -> None:
        person.autopub = True
        person.save()
        client.force_login(user_with_person)

        response = client.get(url)

        assert b"AutoPub will add you" in response.content

    @pytest.mark.parametrize("url", urls)
    def test_next_event_without_response(
        self, client: Client, user_with_person: User, person: Person, url: str
    ) -> None:
        event = create_event(person, days=2)
        client.force_login(user_with_person)

        response = client.get(url)

        assert response.context["next_event"] == event
        assert reverse("pub:events-detail", args=[event.id]).encode() in response.content
        assert b"You haven&#x27;t responded yet" in response.content or b"You haven't responded yet" in response.content

    @pytest.mark.parametrize("url", urls)
    def test_next_event_going(self, client: Client, user_with_person: User, person: Person, url: str) -> None:
        event = create_event(person, days=2)
        PubEventRSVP.objects.create(pub_event=event, person=person, is_attending=True, method=PubEventRSVPMethod.WEB)
        client.force_login(user_with_person)

        response = client.get(url)

        assert response.context["next_event_attendee_count"] == 1
        assert b"going" in response.content

    @pytest.mark.parametrize("url", urls)
    def test_next_event_skipped(self, client: Client, user_with_person: User, person: Person, url: str) -> None:
        event = create_event(person, days=2)
        PubEventRSVP.objects.create(
            pub_event=event, person=person, is_attending=False, method=PubEventRSVPMethod.TOMBSTONE
        )
        client.force_login(user_with_person)

        response = client.get(url)

        assert b"You skipped this one" in response.content


@pytest.mark.django_db
class TestPubOverview:
    url = reverse("pub:overview")

    def test_requires_login(self, client: Client) -> None:
        assert client.get(self.url).status_code == HTTPStatus.FOUND

    def test_lists_only_past_events_as_recent(self, client: Client, user_with_person: User, person: Person) -> None:
        past = create_event(person, days=-3)
        create_event(person, days=3)
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert list(response.context["recent_events"]) == [past]

    @pytest.mark.parametrize(
        ("autopub", "label"), [(True, b'text-bg-success">On<'), (False, b'text-bg-secondary">Off<')]
    )
    def test_shows_autopub_status(
        self, client: Client, user_with_person: User, person: Person, *, autopub: bool, label: bytes
    ) -> None:
        person.autopub = autopub
        person.save()
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert b"Your AutoPub" in response.content
        assert label in response.content

    def test_sub_nav_marks_future_pages(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert response.content.count(b"soon") == 1


@pytest.mark.django_db
class TestEventListView:
    def test_no_longer_embeds_the_next_pub(self, client: Client, user_with_person: User, person: Person) -> None:
        create_event(person, days=2)
        client.force_login(user_with_person)

        response = client.get(reverse("pub:events-list"))

        assert response.status_code == HTTPStatus.OK
        assert b"Next Pub" not in response.content
        assert b"event-details" not in response.content


@pytest.mark.django_db
class TestFerriesPages:
    def test_overview(self, client: Client, user_with_person: User, person: Person) -> None:
        consequence = ConsequenceFactory(created_by=person, is_enabled=True)
        AccusationFactory()
        client.force_login(user_with_person)

        response = client.get(reverse("dashboard:ferries-overview"))

        assert response.status_code == HTTPStatus.OK
        assert list(response.context["my_consequences"]) == [consequence]
        assert len(response.context["recent_accusations"]) == 1

    def test_overview_scoreboard_shows_top_ten(self, client: Client, user_with_person: User) -> None:
        AccusationFactory.create_batch(12)
        client.force_login(user_with_person)

        response = client.get(reverse("dashboard:ferries-overview"))

        assert len(response.context["scoreboard"]) == 10

    def test_overview_redirects_unlinked_users(self, client: Client, user: User) -> None:
        client.force_login(user)

        response = client.get(reverse("dashboard:ferries-overview"))

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("accounts:unlinked_account")

    @pytest.mark.parametrize(
        ("old", "new"),
        [
            ("/score-history/", "dashboard:score-history"),
            ("/accusations/", "dashboard:recent-accusations"),
        ],
    )
    def test_legacy_urls_redirect(self, client: Client, user_with_person: User, old: str, new: str) -> None:
        client.force_login(user_with_person)

        response = client.get(old)

        assert response.status_code == HTTPStatus.MOVED_PERMANENTLY
        assert response["Location"] == reverse(new)

    @pytest.mark.parametrize(
        "name",
        ["dashboard:scoreboard", "dashboard:score-history", "dashboard:recent-accusations", "court:consequence-list"],
    )
    def test_ferries_sub_nav_pages_render(self, client: Client, user_with_person: User, name: str) -> None:
        client.force_login(user_with_person)

        response = client.get(reverse(name))

        assert response.status_code == HTTPStatus.OK
        assert reverse("dashboard:ferries-overview").encode() in response.content


@pytest.mark.django_db
class TestHome:
    def test_scoreboard_shows_top_six(self, client: Client, user_with_person: User) -> None:
        AccusationFactory.create_batch(8)
        client.force_login(user_with_person)

        response = client.get(reverse("dashboard:home"))

        assert len(response.context["scoreboard"]) == 6

    def test_home_hub(self, client: Client, user_with_person: User) -> None:
        AccusationFactory()
        client.force_login(user_with_person)

        response = client.get(reverse("dashboard:home"))

        assert response.status_code == HTTPStatus.OK
        assert response.context["latest_accusation"] is not None
        assert len(response.context["scoreboard"]) <= 6


@pytest.mark.django_db
class TestEventPage:
    def test_links_back_to_events_list(self, client: Client, user_with_person: User, person: Person) -> None:
        event = create_event(person, days=2)
        client.force_login(user_with_person)

        response = client.get(reverse("pub:events-detail", args=[event.id]))

        assert f'<a href="{reverse("pub:events-list")}">&larr; Events</a>'.encode() in response.content


@pytest.mark.django_db
class TestAccusationsPagination:
    url = reverse("dashboard:recent-accusations")

    def test_paginates_accusations(self, client: Client, user_with_person: User) -> None:
        AccusationFactory.create_batch(25)
        client.force_login(user_with_person)

        first = client.get(self.url)
        second = client.get(self.url, {"page": 2})

        assert len(first.context["object_list"]) == 20
        assert first.context["is_paginated"]
        assert b'aria-label="Pagination"' in first.content
        assert len(second.context["object_list"]) == 5


@pytest.mark.django_db
class TestConsequenceCreatePage:
    def test_links_back_to_consequence_list(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.get(reverse("court:consequence-create"))

        assert f'<a href="{reverse("court:consequence-list")}">&larr; My Consequences</a>'.encode() in response.content


@pytest.mark.django_db
class TestManualRSVPPage:
    def test_links_back_to_event(self, client: Client, user_with_person: User, person: Person) -> None:
        event = create_event(person, days=2)
        user_with_person.is_superuser = True
        user_with_person.save()
        client.force_login(user_with_person)

        response = client.get(reverse("pub:events-manual-rsvp", args=[event.id]))

        assert response.status_code == HTTPStatus.OK
        assert (
            f'<a href="{reverse("pub:events-detail", args=[event.id])}">&larr; Event</a>'.encode() in response.content
        )
