"""App URLs"""

from django.urls import path, re_path

from assets import views
from assets.api import api

app_name: str = "assets"

urlpatterns = [
    path("", views.index, name="index"),
    path("add_corp/", views.add_corp, name="add_corp"),
    path("add_char/", views.add_char, name="add_char"),
    path("create_order", views.create_order, name="create_order"),
    path(
        "requests/<int:request_id>/in_progress",
        views.mark_request_in_progress,
        name="request_in_progress",
    ),
    path(
        "requests/<int:request_id>/canceled",
        views.mark_request_canceled,
        name="request_canceled",
    ),
    # -- API System
    re_path(r"^api/", api.urls),
]
