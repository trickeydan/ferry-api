# type: ignore
import os

from .base import *  # noqa: F403

ALLOWED_HOSTS = ["ferry.containers-dev.sown.org.uk"]
CSRF_TRUSTED_ORIGINS = ["https://ferry.containers-dev.sown.org.uk"]

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


SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")