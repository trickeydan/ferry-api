from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ferry.accounts"

    def ready(self) -> None:
        from ferry.core import permissions  # noqa: F401
