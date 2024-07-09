from typing import Any

import requests
from django.conf import settings


class NoSuchGuildMemberError(Exception):
    pass


class DiscordClient:
    def __init__(self, bot_token: str) -> None:
        self._bot_token = bot_token

    def _request(self, method: str, endpoint: str) -> Any:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bot {self._bot_token}",
        }
        resp = requests.request(method, f"https://discord.com/api/v10/{endpoint}", headers=headers, timeout=2)
        resp.raise_for_status()
        return resp.json()

    def get_guild_member_by_id(self, guild_id: int, user_id: int) -> dict[str, Any]:
        try:
            return self._request("GET", f"guilds/{guild_id}/members/{user_id}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise NoSuchGuildMemberError() from None
            else:
                raise


def get_discord_client() -> DiscordClient:
    return DiscordClient(settings.DISCORD_TOKEN)
