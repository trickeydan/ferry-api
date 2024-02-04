from django.http import HttpRequest
from ninja import NinjaAPI
from ninja.security import HttpBearer

from ferry.accounts.api import router as accounts_api
from ferry.accounts.models import APIToken


class TokenAuth(HttpBearer):
    def authenticate(self, request: HttpRequest, token: str) -> str | None:
        try:
            api_token = APIToken.objects.filter(is_active=True).get(token=token)
            request.user = api_token.user
            return token
        except APIToken.DoesNotExist:
            return None


api = NinjaAPI(
    title="Ferry API",
    auth=TokenAuth(),
)

api.add_router("/users", accounts_api)

urls = api.urls
