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
    path("", views.index, name="index"),
    path("admin/", views.admin, name="admin"),
    path("location/", views.location, name="location"),
    path("<int:location_id>/flag/<str:location_flag>", views.assets, name="assets"),
    path("add_corp/", views.add_corp, name="add_corp"),
    path("add_char/", views.add_char, name="add_char"),
    path(
        "create_order/<int:location_id>/flag/<str:location_flag>",
        views.create_order,
        name="create_order",
    ),
    path("requests/manage/", views.requests, name="requests"),
    path(
        "requests/<int:request_id>/canceled",
        views.mark_request_canceled,
        name="request_canceled",
    ),
    path(
        "requests/<int:request_id>/completed",
        views.mark_request_completed,
        name="request_completed",
    ),
    path(
        "requests/<int:request_id>/open",
        views.mark_request_open,
        name="request_open",
    ),
    # -- API System
    re_path(r"^api/", (api_patterns, api_app_name, api_namespace)),
]
