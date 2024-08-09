from http import HTTPStatus
from typing import Any

from ferry.accounts.models import User


class APITest:
    def get_headers(self, user: User) -> dict[str, str]:
        api_token = user.api_tokens.create(is_active=True)
        return {
            "Authorization": f"Bearer {api_token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def assert_forbidden(self, resp: Any, *, message: str = "You don't have permission to perform that action") -> None:
        assert resp.status_code == HTTPStatus.FORBIDDEN
        data = resp.json()
        assert data == {
            "status": "error",
            "status_code": 403,
            "status_name": "FORBIDDEN",
            "detail": message,
        }
