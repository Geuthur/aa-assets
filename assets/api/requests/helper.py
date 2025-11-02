# Django
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import resolve_url
from django.utils.html import format_html
from django.utils.translation import gettext as _

# AA Assets
from assets.api.helpers import generate_button
from assets.models import Request


def _request_list(assets_request: Request, perm: bool, request: WSGIRequest) -> str:
    """Generate the request list for the request table"""
    if not perm:
        return ""

    order_button = generate_button(
        "assets/partials/buttons/confirm.html",
        assets_request,
        {
            "title": _("Get Order Information"),
            "modal": "modalViewOrderContainer",
            "icon": "fas fa-info",
            "action": resolve_url("assets:api:get_request_order", assets_request.pk),
            "color": "primary",
            "ajax": "ajax-order",
        },
        request,
    )
    return format_html(order_button)


def _request_actions(assets_request: Request, perm: bool, request: WSGIRequest) -> str:
    """Generate the action buttons for the request table"""
    if not perm:
        return ""
    actions = []

    if assets_request.status == Request.STATUS_OPEN:
        cancel_button = generate_button(
            "assets/partials/buttons/confirm.html",
            assets_request,
            {
                "title": _("Mark Request as Canceled"),
                "text": _("Cancel Request for {requestor} - ID: {request_id}").format(
                    requestor=assets_request.requesting_user.username,
                    request_id=assets_request.pk,
                ),
                "modal": "assets-confirm-request",
                "icon": "fas fa-xmark",
                "action": resolve_url("assets:request_canceled", assets_request.pk),
                "color": "danger",
                "ajax": "action",
            },
            request,
        )
        actions.append(cancel_button)

        confirm_button = generate_button(
            "assets/partials/buttons/confirm.html",
            assets_request,
            {
                "title": _("Mark Request as Completed"),
                "text": _("Complete Request for {requestor} - ID: {request_id}").format(
                    requestor=assets_request.requesting_user.username,
                    request_id=assets_request.pk,
                ),
                "modal": "assets-confirm-request",
                "icon": "fas fa-clipboard-check",
                "action": resolve_url("assets:request_completed", assets_request.pk),
                "color": "success",
                "ajax": "action",
            },
            request,
        )
        actions.append(confirm_button)
    elif assets_request.status == Request.STATUS_CANCELLED:
        reopen_button = generate_button(
            "assets/partials/buttons/confirm.html",
            assets_request,
            {
                "title": _("Mark Request as Open"),
                "text": _("Reopen Request for {requestor} - ID: {request_id}").format(
                    requestor=assets_request.requesting_user.username,
                    request_id=assets_request.pk,
                ),
                "modal": "assets-confirm-request",
                "icon": "fas fa-undo",
                "action": resolve_url("assets:request_open", assets_request.pk),
                "color": "warning",
                "ajax": "action",
            },
            request,
        )
        actions.append(reopen_button)
    actions_html = format_html("".join(actions))

    return format_html('<div class="d-flex justify-content-end">{}</div>', actions_html)


def _my_request_actions(
    assets_request: Request, perm: bool, request: WSGIRequest
) -> str:
    """Generate the action buttons for the request table"""
    if not perm:
        return ""

    actions = []
    if assets_request.status == Request.STATUS_OPEN:
        cancel_button = generate_button(
            "assets/partials/buttons/confirm.html",
            assets_request,
            {
                "title": _("Mark Request as Canceled"),
                "text": _("Cancel Request for {requestor} - ID: {request_id}").format(
                    requestor=assets_request.requesting_user.username,
                    request_id=assets_request.pk,
                ),
                "modal": "assets-confirm-request",
                "icon": "fas fa-xmark",
                "action": resolve_url("assets:request_canceled", assets_request.pk),
                "color": "danger",
                "ajax": "action",
            },
            request,
        )
        actions.append(cancel_button)
    elif assets_request.status == Request.STATUS_CANCELLED:
        reopen_button = generate_button(
            "assets/partials/buttons/confirm.html",
            assets_request,
            {
                "title": _("Mark Request as Open"),
                "text": _("Reopen Request for {requestor} - ID: {request_id}").format(
                    requestor=assets_request.requesting_user.username,
                    request_id=assets_request.pk,
                ),
                "modal": "assets-confirm-request",
                "icon": "fas fa-undo",
                "action": resolve_url("assets:request_open", assets_request.pk),
                "color": "warning",
                "ajax": "action",
            },
            request,
        )
        actions.append(reopen_button)
    actions_html = format_html("".join(actions))

    return format_html('<div class="d-flex justify-content-end">{}</div>', actions_html)
