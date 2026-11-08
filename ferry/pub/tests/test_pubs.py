from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import User
from ferry.pub.models import Pub

HTMX = {"HX-Request": "true"}


def make_pub(name: str, *, is_default: bool = False, is_active: bool = True, emoji: str = "🍺") -> Pub:
    return Pub.objects.create(
        name=name, emoji=emoji, map_url="https://example.com/map", is_default=is_default, is_active=is_active
    )


@pytest.fixture
def admin_with_person() -> User:
    return User.objects.create(username="admin_with_person", person=PersonFactory.create(), is_superuser=True)


@pytest.mark.django_db
class TestPubList:
    url = reverse("pub:pubs-list")

    def test_requires_login(self, client: Client) -> None:
        assert client.get(self.url).status_code == HTTPStatus.FOUND

    def test_default_first_then_alphabetical_and_hides_inactive(self, client: Client, user_with_person: User) -> None:
        make_pub("Zebra")
        make_pub("Apple")
        make_pub("Middle", is_default=True)
        make_pub("Closed", is_active=False)
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert [pub.name for pub in response.context["object_list"]] == ["Middle", "Apple", "Zebra"]
        assert b"Closed" not in response.content

    def test_shows_links_and_default_badge(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("The Anchor", is_default=True)
        pub.menu_url = "https://example.com/menu"
        pub.booking_url = "https://example.com/book"
        pub.save()
        client.force_login(user_with_person)

        content = client.get(self.url).content.decode()

        assert "🍺 The Anchor" in content
        assert ">Default<" in content
        assert 'href="https://example.com/menu"' in content
        assert 'href="https://example.com/book"' in content

    def test_make_default_offered_to_admins(self, client: Client, admin_with_person: User) -> None:
        make_pub("Other")
        client.force_login(admin_with_person)

        assert "Make default" in client.get(self.url).content.decode()

    def test_make_default_not_offered_to_regular_users(self, client: Client, user_with_person: User) -> None:
        make_pub("Other")
        client.force_login(user_with_person)

        assert "Make default" not in client.get(self.url).content.decode()


@pytest.mark.django_db
class TestPubCreate:
    url = reverse("pub:pubs-create")

    def test_requires_login(self, client: Client) -> None:
        assert client.get(self.url).status_code == HTTPStatus.FOUND

    def test_form_uses_emoji_picker(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        content = client.get(self.url).content.decode()

        assert "emoji_picker/emoji-picker.js" in content
        assert "dep-container" in content

    def test_anyone_can_add_a_pub(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.post(self.url, {"name": "The Crown", "emoji": "🍻", "map_url": "https://example.com/crown"})

        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("pub:pubs-list")
        pub = Pub.objects.get(name="The Crown")
        assert pub.emoji == "🍻"
        assert not pub.is_default
        assert pub.is_active

    def test_cannot_set_default_when_adding(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        client.post(
            self.url,
            {"name": "Sneaky", "emoji": "🍻", "map_url": "https://example.com/m", "is_default": "on"},
        )

        assert not Pub.objects.get(name="Sneaky").is_default

    def test_rejects_duplicate_name(self, client: Client, user_with_person: User) -> None:
        make_pub("The Crown")
        client.force_login(user_with_person)

        response = client.post(self.url, {"name": "The Crown", "emoji": "🍻", "map_url": "https://example.com/m"})

        assert response.status_code == HTTPStatus.OK
        assert Pub.objects.filter(name="The Crown").count() == 1

    def test_rejects_more_than_one_character(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.post(self.url, {"name": "Two", "emoji": "🍻🍺", "map_url": "https://example.com/m"})

        assert response.status_code == HTTPStatus.OK
        assert "Pick a single emoji." in response.content.decode()
        assert not Pub.objects.filter(name="Two").exists()


@pytest.mark.django_db
class TestPubEdit:
    def url(self, pub: Pub) -> str:
        return reverse("pub:pubs-edit", args=[pub.id])

    def test_requires_login(self, client: Client) -> None:
        assert client.get(self.url(make_pub("Anchor"))).status_code == HTTPStatus.FOUND

    def test_form_is_prefilled_with_emoji_picker(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("The Anchor", emoji="🍻")
        client.force_login(user_with_person)

        content = client.get(self.url(pub)).content.decode()

        assert 'value="The Anchor"' in content
        assert 'value="🍻"' in content
        assert "emoji_picker/emoji-picker.js" in content
        assert "Edit The Anchor" in content

    def test_anyone_can_edit_a_pub(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("The Anchor")
        client.force_login(user_with_person)

        response = client.post(
            self.url(pub),
            {
                "name": "The Old Anchor",
                "emoji": "⚓",
                "map_url": "https://example.com/new",
                "menu_url": "https://example.com/menu",
                "booking_url": "",
            },
        )

        pub.refresh_from_db()
        assert response.status_code == HTTPStatus.FOUND
        assert response["Location"] == reverse("pub:pubs-list")
        assert (pub.name, pub.emoji, pub.map_url, pub.menu_url) == (
            "The Old Anchor",
            "⚓",
            "https://example.com/new",
            "https://example.com/menu",
        )

    def test_cannot_change_default_or_active_by_posting_them(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("The Anchor")
        client.force_login(user_with_person)

        client.post(
            self.url(pub),
            {
                "name": "The Anchor",
                "emoji": "🍺",
                "map_url": "https://example.com/map",
                "is_default": "on",
                "is_active": "",
            },
        )

        pub.refresh_from_db()
        assert not pub.is_default
        assert pub.is_active

    def test_keeping_own_name_is_not_a_duplicate(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("The Anchor")
        client.force_login(user_with_person)

        response = client.post(
            self.url(pub), {"name": "The Anchor", "emoji": "🍻", "map_url": "https://example.com/map"}
        )

        assert response.status_code == HTTPStatus.FOUND

    def test_rejects_another_pubs_name(self, client: Client, user_with_person: User) -> None:
        make_pub("The Crown")
        pub = make_pub("The Anchor")
        client.force_login(user_with_person)

        response = client.post(self.url(pub), {"name": "The Crown", "emoji": "🍺", "map_url": "https://example.com/m"})

        pub.refresh_from_db()
        assert response.status_code == HTTPStatus.OK
        assert pub.name == "The Anchor"

    def test_inactive_pub_not_found(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("Closed", is_active=False)
        client.force_login(user_with_person)

        assert client.get(self.url(pub)).status_code == HTTPStatus.NOT_FOUND

    def test_edit_link_on_pubs_page_but_not_overview(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("The Anchor")
        client.force_login(user_with_person)

        pubs_page = client.get(reverse("pub:pubs-list")).content.decode()
        overview = client.get(reverse("pub:overview")).content.decode()

        assert self.url(pub) in pubs_page
        assert self.url(pub) not in overview


@pytest.mark.django_db
class TestSetDefaultPub:
    def url(self, pub: Pub) -> str:
        return reverse("pub:pubs-set-default", args=[pub.id])

    def test_admin_sets_default_and_demotes_previous(self, client: Client, admin_with_person: User) -> None:
        old = make_pub("Old", is_default=True)
        new = make_pub("New")
        client.force_login(admin_with_person)

        response = client.post(self.url(new), headers=HTMX)

        old.refresh_from_db()
        new.refresh_from_db()
        assert response.status_code == HTTPStatus.OK
        assert new.is_default
        assert not old.is_default
        assert b'id="pubs-table"' in response.content
        assert [pub.name for pub in response.context["pubs"]] == ["New", "Old"]

    def test_regular_user_forbidden(self, client: Client, user_with_person: User) -> None:
        pub = make_pub("New")
        client.force_login(user_with_person)

        response = client.post(self.url(pub), headers=HTMX)

        pub.refresh_from_db()
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert not pub.is_default

    def test_requires_htmx(self, client: Client, admin_with_person: User) -> None:
        pub = make_pub("New")
        client.force_login(admin_with_person)

        assert client.post(self.url(pub)).status_code == HTTPStatus.BAD_REQUEST

    def test_cannot_default_an_inactive_pub(self, client: Client, admin_with_person: User) -> None:
        pub = make_pub("Closed", is_active=False)
        client.force_login(admin_with_person)

        assert client.post(self.url(pub), headers=HTMX).status_code == HTTPStatus.NOT_FOUND


@pytest.mark.django_db
class TestPubsOnOverview:
    def test_overview_lists_pubs_with_default(self, client: Client, user_with_person: User) -> None:
        make_pub("Plain")
        make_pub("Favourite", is_default=True)
        client.force_login(user_with_person)

        response = client.get(reverse("pub:overview"))

        assert [pub.name for pub in response.context["pubs"]] == ["Favourite", "Plain"]
        assert reverse("pub:pubs-list").encode() in response.content
        assert b"Make default" not in response.content
