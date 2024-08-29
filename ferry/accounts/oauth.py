from authlib.integrations.django_client import OAuth
from django.conf import settings

oauth_config = OAuth()

# SOWN SSO
oauth_config.register(
    "sown",
    client_id=settings.SSO_OIDC_CLIENT_ID,
    client_secret=settings.SSO_OIDC_CLIENT_SECRET,
    server_metadata_url=settings.SSO_OIDC_CONFIGURATION_URL,
    client_kwargs={"scope": settings.SSO_OIDC_SCOPES},
)
