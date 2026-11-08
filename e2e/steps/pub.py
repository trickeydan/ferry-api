"""Steps for the pub events, RSVP, skipping and pub night features."""

from collections.abc import Callable
from datetime import timedelta

import requests
from django.utils import timezone
from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then, when
from pytest_django.live_server_helper import LiveServer

from e2e.steps.helpers import person_of
from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import User
from ferry.pub.models import Pub, PubEvent, PubEventRSVP, PubEventRSVPMethod
from ferry.pub.services import skip_next_pub


@given(parsers.parse('the next pub is at "{pub_name}"'), target_fixture="next_event")
def next_pub(current_user: User, pub_name: str) -> PubEvent:
    pub, _ = Pub.objects.get_or_create(name=pub_name, defaults={"emoji": "🍺", "map_url": "https://example.com/map"})
    return PubEvent.objects.create(
        timestamp=timezone.now() + timedelta(days=2), pub=pub, created_by=person_of(current_user)
    )


@given("I am going to it through AutoPub")
def going_through_autopub(current_user: User, next_event: PubEvent) -> None:
    PubEventRSVP.objects.create(
        pub_event=next_event, person=person_of(current_user), is_attending=True, method=PubEventRSVPMethod.AUTO
    )


@given("I have skipped the next pub")
def have_skipped(current_user: User) -> None:
    skip_next_pub(person_of(current_user))


@when("I open the next pub's page")
def open_next_pub_page(goto: Callable[[str], None], next_event: PubEvent) -> None:
    goto(f"/pub/events/{next_event.id}/")


@given(parsers.parse('"{name}" is a member using AutoPub'))
def member_using_autopub(name: str) -> None:
    PersonFactory.create(display_name=name, autopub=True)


@given(parsers.parse('"{name}" is a member not using AutoPub'))
def member_not_using_autopub(name: str) -> None:
    PersonFactory.create(display_name=name, autopub=False)


@when(parsers.parse('an admin schedules a pub night at "{pub_name}" for next week'), target_fixture="next_event")
def admin_schedules_pub_night(live_server: LiveServer, pub_name: str) -> PubEvent:
    """Create the event the way the Discord bot does, through the API, so AutoPub RSVPs are created too."""
    admin = User.objects.create(username="scheduler", person=PersonFactory.create(), is_superuser=True)
    token = admin.api_tokens.create(name="bot", is_active=True)
    pub, _ = Pub.objects.get_or_create(name=pub_name, defaults={"emoji": "🍺", "map_url": "https://example.com/map"})

    response = requests.post(
        f"{live_server.url}/api/v2/pub/events/",
        json={
            "timestamp": (timezone.now() + timedelta(days=7)).isoformat(),
            "pub": str(pub.id),
            "created_by": str(person_of(admin).id),
        },
        headers={"Authorization": f"Bearer {token.token}"},
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return PubEvent.objects.get(pk=response.json()["id"])


@when("the pub night has happened")
def pub_night_has_happened(next_event: PubEvent) -> None:
    PubEvent.objects.filter(pk=next_event.pk).update(timestamp=timezone.now() - timedelta(hours=2))


@then(parsers.parse("the pub stats should show {events:d} event with an average of {average} attendees"))
def pub_stats(page: Page, events: int, average: str) -> None:
    card = page.locator(".card", has_text="events this academic year")
    expect(card.locator(".display-6").first).to_have_text(str(events))
    expect(card.locator(".display-6").nth(1)).to_have_text(average)


@then(parsers.parse('"{name}" should have a pub streak of {streak:d}'))
def pub_streak(page: Page, name: str, streak: int) -> None:
    expect(page.get_by_role("row", name=name).locator("td").first).to_have_text(str(streak))
