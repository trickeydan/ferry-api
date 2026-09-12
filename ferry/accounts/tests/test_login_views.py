from unittest.mock import patch

import pytest
from django.http import HttpResponseRedirect
from django.test import Client
from django.urls import reverse

from ferry.accounts.models import Person, User


@pytest.mark.django_db
def test_login_page_is_rendered(client: Client) -> None:
    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert b"Login with SOWN" in response.content
    assert b"Login with Discord" in response.content


@pytest.mark.django_db
def test_discord_login_redirects_to_discord_with_callback_url(client: Client) -> None:
    login_url = reverse("accounts:discord_login")
    callback_url = reverse("accounts:sso_discord_redirect")

    with patch("ferry.accounts.views.oauth_config.discord.authorize_redirect") as authorize_redirect:
        authorize_redirect.return_value = HttpResponseRedirect("https://discord.com/oauth2/authorize")

        response = client.get(login_url, {"next": "/dashboard/"})

    assert response.status_code == 302
    assert response["Location"] == "https://discord.com/oauth2/authorize"
    assert client.session["sso_next"] == "/dashboard/"
    request = authorize_redirect.call_args.args[0]
    assert request.build_absolute_uri(callback_url) == f"http://testserver{callback_url}"


@pytest.mark.django_db
def test_discord_callback_logs_in_user_linked_to_discord_id(client: Client) -> None:
    person = Person.objects.create(display_name="Discord User", discord_id=1234)
    user = User.objects.create_user(username="sown-user", person=person)
    callback_url = reverse("accounts:sso_discord_redirect")

    with (
        patch(
            "ferry.accounts.views.oauth_config.discord.authorize_access_token",
            return_value={"access_token": "token"},
        ),
        patch("ferry.accounts.views.oauth_config.discord.get") as get_user,
        patch("ferry.accounts.views.get_discord_client") as get_discord_client,
    ):
        get_user.return_value.json.return_value = {"id": "1234"}
        get_discord_client.return_value.get_guild_member_by_id.return_value = {"user": {"username": "discord-user"}}
        response = client.get(callback_url)

    assert response.status_code == 302
    assert response["Location"] == "/"
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_discord_callback_creates_user_and_person_for_guild_member(client: Client) -> None:
    callback_url = reverse("accounts:sso_discord_redirect")

    with (
        patch(
            "ferry.accounts.views.oauth_config.discord.authorize_access_token",
            return_value={"access_token": "token"},
        ),
        patch("ferry.accounts.views.oauth_config.discord.get") as get_user,
        patch("ferry.accounts.views.get_discord_client") as get_discord_client,
    ):
        get_user.return_value.json.return_value = {"id": "1234"}
        get_discord_client.return_value.get_guild_member_by_id.return_value = {
            "nick": "Guild Nickname",
            "user": {"username": "discord-user"},
        }
        response = client.get(callback_url)

    person = Person.objects.get(discord_id=1234)
    user = User.objects.get(person=person)
    assert person.display_name == "Guild Nickname"
    assert user.username == "discord-1234"
    assert response.status_code == 302
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_sown_login_redirects_to_sown_with_callback_url(client: Client) -> None:
    login_url = reverse("accounts:sown_login")
    callback_url = reverse("accounts:sso_oidc_redirect")

    with patch("ferry.accounts.views.oauth_config.sown.authorize_redirect") as authorize_redirect:
        authorize_redirect.return_value = HttpResponseRedirect("https://sso.example/authorize")

        response = client.get(login_url, {"next": "/dashboard/"})

    assert response.status_code == 302
    assert response["Location"] == "https://sso.example/authorize"
    assert client.session["sso_next"] == "/dashboard/"
    request = authorize_redirect.call_args.args[0]
    assert request.build_absolute_uri(callback_url) == f"http://testserver{callback_url}"
