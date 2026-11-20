# Standard Library
from datetime import datetime
from typing import Any

# Third Party
from ninja import Field, Schema


class Message(Schema):
    message: str


class ErrorSchema(Schema):
    """Error response of an endpoint, e.g. for 403 and 404."""

    error: str


class UserSettingsSchema(Schema):
    disable_notifications: bool


class UserSettingsUpdateRequest(Schema):
    disable_notifications: bool


class Character(Schema):
    character_name: str
    character_id: int
    corporation_id: int
    corporation_name: str
    alliance_id: int | None = None
    alliance_name: str | None = None


class Corporation(Schema):
    corporation_id: int
    corporation_name: str
    alliance_id: int | None = None
    alliance_name: str | None = None


class EveName(Schema):
    id: int
    name: str
    cat: str | None = None


class Requests(Schema):
    id: int
    status: str
    action: str
    created: datetime
    closed: datetime | None = None
    approver: Any | None
    requestor: Any
    can_cancel: bool = False
    can_complete: bool = False
    can_reopen: bool = False


class ActionResponse(Schema):
    """Response of an action endpoint, e.g. after creating an order."""

    success: bool
    message: str


# General


class UserData(Schema):
    """The user and their main character, with the rights the frontend needs."""

    user_id: int
    character_id: int
    character_name: str
    corporation_id: int
    corporation_name: str
    alliance_id: int | None = None
    alliance_name: str | None = None
    portrait: str | None = None

    is_admin: bool = False
    can_manage_requests: bool = False
    can_add_corporation: bool = False


class MenuLink(Schema):
    """
    Represents a link in the menu.

    Parameters:
        name (str): The name of the menu link.
        link (str | None): The URL or path the menu link points to.
        is_external (bool): Indicates if the link leaves the React app.
        badge (int | None): Number shown as badge next to the link.
        has_errors (bool): Whether the badge pulses because of active errors.
    """

    name: str
    link: str = None
    is_external: bool = False
    badge: int | None = None
    has_errors: bool = False


class MenuSchema(Schema):
    """Schema for the overall menu."""

    left_links: list[MenuLink] = []
    right_links: list[MenuLink] = []


class AdminTasksRequest(Schema):
    """Request body of the administration tasks."""

    force_refresh: bool = False
    clear_etags: bool = False
    update_assets: bool = False
    update_locations: bool = False
    update_parent_locations: bool = False


# Owners


class OwnerUpdateStatusSchema(Schema):
    """Update status of one section of an owner."""

    section: str
    section_label: str
    is_success: bool | None = None
    has_token_error: bool = False
    error_message: str = ""
    last_run_finished_at: datetime | None = None
    last_update_finished_at: datetime | None = None


class OwnerSchema(Schema):
    """An owner (character or corporation) with its aggregate update status."""

    id: int
    name: str
    owner_type: str
    character_id: int | None = None
    corporation_id: int | None = None
    active: bool
    update_status: str
    update_status_label: str
    last_update: datetime | None = None


class OwnerDetailSchema(OwnerSchema):
    """An owner with the status of every section."""

    sections: list[OwnerUpdateStatusSchema] = []


# Locations and assets


class LocationSchema(Schema):
    location_id: int
    name: str | None = None
    solar_system: str | None = None


class AssetSchema(Schema):
    asset_pk: int
    item_id: int
    type_id: int
    name: str
    quantity: int
    location_id: int
    location: str | None = None
    location_flag: str
    price: float | None = None


class Assets(Schema):
    location_id: int
    location_flag: str
    assets: list[AssetSchema]


# Requests


class OrderItemRequest(Schema):
    asset_pk: int
    amount: int = Field(..., ge=1)


class OrderCreateRequest(Schema):
    items: list[OrderItemRequest] = Field(..., min_length=1)


class RequestItemSchema(Schema):
    type_id: int
    name: str
    quantity: int


class RequestDetailSchema(Schema):
    id: int
    status: str
    status_label: str
    requestor: str
    approver: str | None = None
    created: datetime
    closed: datetime | None = None
    items: list[RequestItemSchema]
