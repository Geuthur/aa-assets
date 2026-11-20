"""Order endpoints: create orders and change their status."""

# Standard Library
from http import HTTPStatus

# Third Party
from ninja import NinjaAPI

# Django
from django.core.handlers.wsgi import WSGIRequest
from django.utils.translation import gettext

# AA Assets
from assets.api import schema
from assets.helpers.orders import (
    MODE_CANCELED,
    MODE_COMPLETED,
    MODE_OPEN,
    change_request_status,
    cooldown_message,
    create_order,
    exceeds_message,
    get_apr_cooldown,
)
from assets.managers import GeneralManager
from assets.models import Assets, Request, RequestAssets
from assets.providers import logger

# The status an order needs before each change (matches `request_permissions`)
_FROM_STATUS = {
    MODE_CANCELED: Request.STATUS_OPEN,
    MODE_COMPLETED: Request.STATUS_OPEN,
    MODE_OPEN: Request.STATUS_CANCELLED,
}


class OrdersApiEndpoints:
    tags = ["Requests"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "requests/{request_id}/",
            response={
                HTTPStatus.OK: schema.RequestDetailSchema,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
                HTTPStatus.NOT_FOUND: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Get an order with its items",
        )
        def get_request(request: WSGIRequest, request_id: int):
            user_request = (
                Request.objects.select_related("requesting_user", "approver_user")
                .filter(pk=request_id)
                .first()
            )
            if user_request is None:
                return HTTPStatus.NOT_FOUND, {
                    "error": gettext("Request does not exist")
                }

            if (
                not Request.objects.visible_to(request.user)
                .filter(pk=request_id)
                .exists()
            ):
                return HTTPStatus.FORBIDDEN, {"error": gettext("Permission Denied")}

            items = RequestAssets.objects.filter(request=user_request).select_related(
                "eve_type"
            )
            return HTTPStatus.OK, schema.RequestDetailSchema(
                id=user_request.pk,
                status=user_request.status,
                status_label=user_request.get_status_display(),
                requestor=user_request.requesting_user.username,
                approver=(
                    user_request.approver_user.username
                    if user_request.approver_user
                    else None
                ),
                created=user_request.created_at,
                closed=user_request.closed_at,
                items=[
                    schema.RequestItemSchema(
                        type_id=item.eve_type.id,
                        name=item.eve_type.name,
                        quantity=item.quantity,
                    )
                    for item in items
                ],
            )

        @api.post(
            "orders/",
            response={
                HTTPStatus.OK: schema.ActionResponse,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
                HTTPStatus.NOT_FOUND: schema.ErrorSchema,
                HTTPStatus.CONFLICT: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Create an order of one or more assets",
        )
        def post_order(request: WSGIRequest, payload: schema.OrderCreateRequest):
            visible_assets = Assets.objects.visible_to(request.user).select_related(
                "eve_type", "location"
            )
            # The same asset twice counts as one item with the summed amount
            amounts: dict[int, int] = {}
            for item in payload.items:
                amounts[item.asset_pk] = amounts.get(item.asset_pk, 0) + item.amount

            items = []
            for asset_pk, amount in amounts.items():
                asset = visible_assets.filter(pk=asset_pk).first()
                if asset is None:
                    return HTTPStatus.NOT_FOUND, {
                        "error": gettext("The asset does not exist.")
                    }
                items.append((asset, amount))

            user_request, exceeds_items = create_order(request.user, items)

            if user_request is None:
                return HTTPStatus.CONFLICT, {
                    "error": gettext("Requested amount exceeds available quantity.")
                }
            if exceeds_items:
                return HTTPStatus.CONFLICT, {"error": exceeds_message(exceeds_items)}

            logger.info("User %s created order %s", request.user, user_request.pk)
            return HTTPStatus.OK, schema.ActionResponse(
                success=True, message=gettext("Order created successfully.")
            )

        def _change_status(request: WSGIRequest, request_id: int, mode: str):
            user_request = Request.objects.filter(pk=request_id).first()
            if user_request is None:
                return HTTPStatus.NOT_FOUND, {
                    "error": gettext("Request does not exist")
                }

            if user_request.status != _FROM_STATUS[mode]:
                return HTTPStatus.CONFLICT, {
                    "error": gettext(
                        "The request cannot be changed in its current status."
                    )
                }

            if get_apr_cooldown(request.user, request_id, mode):
                return HTTPStatus.TOO_MANY_REQUESTS, {"error": cooldown_message()}

            is_changed, msg = change_request_status(request.user, user_request, mode)
            if not is_changed:
                return HTTPStatus.FORBIDDEN, {"error": msg}
            return HTTPStatus.OK, schema.ActionResponse(success=True, message=msg)

        status_change_responses = {
            HTTPStatus.OK: schema.ActionResponse,
            HTTPStatus.FORBIDDEN: schema.ErrorSchema,
            HTTPStatus.NOT_FOUND: schema.ErrorSchema,
            HTTPStatus.CONFLICT: schema.ErrorSchema,
            HTTPStatus.TOO_MANY_REQUESTS: schema.ErrorSchema,
        }

        @api.post(
            "requests/{request_id}/cancel/",
            response=status_change_responses,
            tags=self.tags,
            summary="Cancel an open order (requestor or manager)",
        )
        def cancel_request(request: WSGIRequest, request_id: int):
            return _change_status(request, request_id, MODE_CANCELED)

        @api.post(
            "requests/{request_id}/complete/",
            response=status_change_responses,
            tags=self.tags,
            summary="Mark an order as completed (manager)",
        )
        def complete_request(request: WSGIRequest, request_id: int):
            if not GeneralManager.has_manage_requests_access(request.user):
                return HTTPStatus.FORBIDDEN, {"error": gettext("Permission Denied")}
            return _change_status(request, request_id, MODE_COMPLETED)

        @api.post(
            "requests/{request_id}/reopen/",
            response=status_change_responses,
            tags=self.tags,
            summary="Reopen an order (manager)",
        )
        def reopen_request(request: WSGIRequest, request_id: int):
            if not GeneralManager.has_manage_requests_access(request.user):
                return HTTPStatus.FORBIDDEN, {"error": gettext("Permission Denied")}
            return _change_status(request, request_id, MODE_OPEN)
