"""App URLs"""

# Django
from django.urls import path, re_path

# Alliance Auth
from allianceauth.authentication.decorators import decorate_url_patterns

# AA Assets
from assets import views
from assets.api import api
from assets.api.auth import basic_access_required

app_name: str = "assets"  # pylint: disable=invalid-name

# Every URL of the API (endpoints, schema and docs) requires `basic_access`
api_patterns, api_app_name, api_namespace = api.urls
api_patterns = decorate_url_patterns(
    (api_patterns, api_app_name), basic_access_required
)[0]

urlpatterns = [
    path("add_corp/", views.add_corp, name="add_corp"),
    path("add_char/", views.add_char, name="add_char"),
    # -- API System
    re_path(r"^api/", (api_patterns, api_app_name, api_namespace)),
    # -- React Frontend, all other routes are handled by the router
    path("", views.react_base, name="index"),
    re_path(r"^(?!api/).*$", views.react_base, name="react_base"),
]
