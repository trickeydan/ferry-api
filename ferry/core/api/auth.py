from rest_framework import authentication, exceptions

from ferry.accounts.models import APIToken, User


class TokenAuthentication(authentication.TokenAuthentication):
    keyword = "Bearer"

    def authenticate_credentials(self, key: str) -> tuple[User, APIToken]:
        try:
            token = APIToken.objects.select_related("user").get(token=key)
        except APIToken.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid token.") from None

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("User inactive or deleted.")

        if not token.is_active:
            raise exceptions.AuthenticationFailed("Invalid token.")

        return (token.user, token)
