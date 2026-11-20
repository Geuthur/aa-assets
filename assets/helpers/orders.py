"""Order logic shared by the Django views and the API."""

# Standard Library
from dataclasses import dataclass

# Django
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext_lazy as _

# AA Assets
from assets.models import Assets, Request, RequestAssets

COOLDOWN_SECONDS = 60

MODE_CANCELED = "canceled"
MODE_COMPLETED = "completed"
MODE_OPEN = "open"


def build_apr_cooldown_cache_tag(user, request_id, mode):
    return f"cooldown_request_{user}_{request_id}_{mode}"


def get_apr_cooldown(user, request_id, mode) -> bool:
    """Return True while the user is on cooldown for this request and mode."""
    return bool(cache.get(build_apr_cooldown_cache_tag(user, request_id, mode), False))


def set_apr_cooldown(user, request_id, mode):
    """Set a 60 sec cooldown for the Approver"""
    return cache.set(
        build_apr_cooldown_cache_tag(user, request_id, mode), True, COOLDOWN_SECONDS
    )


def cooldown_message() -> str:
    return str(_("You are on cooldown. Please wait 60 seconds before trying again."))


def validate_asset_quantity(asset: Assets, amount: int) -> bool:
    """Validates if the requested amount exceeds the available quantity."""
    requests_obj = RequestAssets.objects.filter(
        asset_pk=asset.pk,
        eve_type=asset.eve_type,
        request__status=Request.STATUS_OPEN,
    ).values_list("quantity", flat=True)
    if requests_obj and sum(requests_obj) + amount > asset.quantity:
        return False
    return True


def create_request_asset_object(
    user_request: Request, asset: Assets, amount: int
) -> RequestAssets:
    """Create a RequestAssets Object."""
    return RequestAssets(
        name=asset.eve_type.name,
        request=user_request,
        asset_pk=asset.pk,
        asset_location_id=asset.location.id,
        asset_location_flag=asset.location_flag,
        eve_type=asset.eve_type,
        quantity=amount,
    )


def create_order(
    user: User, items: list[tuple[Assets, int]]
) -> tuple[Request | None, list[str]]:
    """
    Create one open order with every item whose amount is still available.

    Approvers are notified when the order is saved. Items whose amount
    exceeds the available quantity are left out.

    Returns:
        The saved order (None if no item was available) and the names of
        the items that were left out.
    """
    user_request = Request(requesting_user=user, status=Request.STATUS_OPEN)

    exceeds_items = []
    assets_items = []
    for asset, amount in items:
        if validate_asset_quantity(asset, amount):
            assets_items.append(
                create_request_asset_object(user_request, asset, amount)
            )
        else:
            exceeds_items.append(asset.eve_type.name)

    if not assets_items:
        return None, exceeds_items

    with transaction.atomic():
        user_request.save()
        for asset_request in assets_items:
            asset_request.save()
        user_request.notify_new_request()
    return user_request, exceeds_items


def exceeds_message(exceeds_items: list[str]) -> str:
    return (
        f"The following items exceeds the available quantity {', '.join(exceeds_items)} "
        "and are not included in your order."
    )


@dataclass(frozen=True)
class _StatusChange:
    status: str
    closed: bool
    can_requestor_edit: bool
    message: str


_STATUS_CHANGES = {
    MODE_CANCELED: _StatusChange(
        status=Request.STATUS_CANCELLED,
        closed=True,
        can_requestor_edit=True,
        message=_(
            "The request for Order {user_request_pk} from {user_request_requesting_user} has been closed as cancelled."
        ),
    ),
    MODE_COMPLETED: _StatusChange(
        status=Request.STATUS_COMPLETED,
        closed=True,
        can_requestor_edit=False,
        message=_(
            "The request for Order {user_request_pk} from {user_request_requesting_user} has been closed as completed."
        ),
    ),
    MODE_OPEN: _StatusChange(
        status=Request.STATUS_OPEN,
        closed=False,
        can_requestor_edit=False,
        message=_(
            "The request for Order {user_request_pk} from {user_request_requesting_user} has been reopened."
        ),
    ),
}


def change_request_status(
    user: User, user_request: Request, mode: str
) -> tuple[bool, str]:
    """
    Change the status of an order, set the cooldown and notify.

    `mode` is one of MODE_CANCELED, MODE_COMPLETED and MODE_OPEN. The rights
    are checked by `Request.mark_request`.

    Returns:
        Whether the status was changed and the message for the user.
    """
    change = _STATUS_CHANGES[mode]
    is_changed = user_request.mark_request(
        user=user,
        status=change.status,
        closed=change.closed,
        can_requestor_edit=change.can_requestor_edit,
    )
    format_kwargs = {
        "user_request_pk": user_request.pk,
        "user_request_requesting_user": user_request.requesting_user,
    }

    if not is_changed:
        msg = _(
            "The request for Order {user_request_pk} from {user_request_requesting_user} has failed."
        ).format(**format_kwargs)
        return False, msg

    set_apr_cooldown(user, user_request.pk, mode)
    if mode == MODE_CANCELED:
        user_request.notify_request_canceled(user=user)
    elif mode == MODE_COMPLETED:
        user_request.notify_request_completed()
    else:
        user_request.notify_request_open(user)

    return True, change.message.format(**format_kwargs)
