# type: ignore
import os

from .base import *  # noqa: F403

HOSTNAME = os.environ.get("HOSTNAME", "ferry.example.com")

ALLOWED_HOSTS = [HOSTNAME]
CSRF_TRUSTED_ORIGINS = [f"https://{HOSTNAME}"]

DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ["SECRET_KEY"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("SQL_DATABASE"),
        "USER": os.environ.get("SQL_USER"),
        "PASSWORD": os.environ.get("SQL_PASSWORD"),
        "HOST": os.environ.get("SQL_HOST"),
        "PORT": os.environ.get("SQL_PORT"),
    }
}

MEDIA_ROOT = "/app/media/"
STATIC_ROOT = "/app/static/"

DISCORD_GUILD = os.environ["DISCORD_GUILD"]
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]


# SSO configuration

SSO_OIDC_CONFIGURATION_URL = os.environ["SSO_OIDC_CONFIGURATION_URL"]
SSO_OIDC_CLIENT_ID = os.environ["SSO_OIDC_CLIENT_ID"]
SSO_OIDC_CLIENT_SECRET = os.environ["SSO_OIDC_CLIENT_SECRET"]
SSO_OIDC_SCOPES = "openid email profile"

DISCORD_CLIENT_ID = os.environ["DISCORD_CLIENT_ID"]
DISCORD_CLIENT_SECRET = os.environ["DISCORD_CLIENT_SECRET"]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGOUT_REDIRECT_URL = os.environ.get("LOGOUT_REDIRECT_URL", "https://google.com/")
