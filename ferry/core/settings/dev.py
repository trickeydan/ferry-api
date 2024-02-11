# type: ignore
from .base import *  # noqa: F403

DEBUG = True

SECURE_SSL_REDIRECT = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-CHANGEME!!!"  # noqa: S105

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
    }
}

try:
    from .local import *  # noqa
except ImportError:
    pass
