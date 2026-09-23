from authlib.integrations.django_client import OAuth
from django.conf import settings

oauth_config = OAuth()

# Discord
oauth_config.register(
    "discord",
    client_id=settings.DISCORD_CLIENT_ID,
    client_secret=settings.DISCORD_CLIENT_SECRET,
    access_token_url="https://discord.com/api/oauth2/token",  # noqa: S106
    authorize_url="https://discord.com/api/oauth2/authorize",
    api_base_url="https://discord.com/api/",
    client_kwargs={"scope": "identify"},
)
