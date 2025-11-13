# Third Party
from ninja import NinjaAPI
from ninja.security import django_auth

# Django
from django.conf import settings

# AA Assets
from assets.api import assets, requests
from assets.hooks import get_extension_logger

logger = get_extension_logger(__name__)

api = NinjaAPI(
    title="Geuthur API",
    version="0.1.0",
    urls_namespace="assets:api",
    auth=django_auth,
    openapi_url=settings.DEBUG and "/openapi.json" or "",
)

# Add the character endpoints
assets.setup(api)
# Add the character endpoints
requests.setup(api)
