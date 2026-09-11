from django.conf import settings


def app_name(request: object) -> dict[str, str]:
    return {"app_name": settings.APP_NAME}