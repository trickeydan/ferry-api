from unittest.mock import patch

import pytest
from django.http import HttpResponseRedirect
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
def test_login_page_is_rendered(client: Client) -> None:
    response = client.get(reverse("accounts:login"))

    assert response.status_code == 200
    assert b"Login with SOWN" in response.content


@pytest.mark.django_db
def test_login_button_redirects_to_sown_with_callback_url(client: Client) -> None:
    login_url = reverse("accounts:login")
    callback_url = reverse("accounts:sso_oidc_redirect")

    with patch("ferry.accounts.views.oauth_config.sown.authorize_redirect") as authorize_redirect:
        authorize_redirect.return_value = HttpResponseRedirect("https://sso.example/authorize")

        response = client.post(login_url, {"next": "/dashboard/"})

    assert response.status_code == 302
    assert response["Location"] == "https://sso.example/authorize"
    assert client.session["sso_next"] == "/dashboard/"
    request = authorize_redirect.call_args.args[0]
    assert request.build_absolute_uri(callback_url) == f"http://testserver{callback_url}"
