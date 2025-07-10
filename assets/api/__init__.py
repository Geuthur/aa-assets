from ninja import NinjaAPI
from ninja.security import django_auth

from django.conf import settings

from assets.api import assets, requests
from assets.hooks import get_extension_logger

logger = get_extension_logger(__name__)

api = NinjaAPI(
    title="Geuthur API",
    version="0.1.0",
    urls_namespace="assets:api",
    auth=django_auth,
    csrf=True,
    openapi_url=settings.DEBUG and "/openapi.json" or "",
)

# Add the character endpoints
assets.setup(api)
# Add the character endpoints
requests.setup(api)
