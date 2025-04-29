from django.contrib.humanize.templatetags.humanize import intcomma
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import resolve_url

from assets.models import Request
from assets.api.helpers import generate_button
   
def _request_actions(assets_request: Request, perms, request: WSGIRequest) -> str:
    """Generate the action buttons for the request table"""
    if not perms:
        return ""

    actions = []
    
    if assets_request.status == Request.STATUS_OPEN:
        cancel_button = generate_button(
            "assets/partials/buttons/confirm.html",
            assets_request,
            {
                "title": _("Delete Request"),
                "text": _("Delete Request for {requestor} - ID: {request_id}").format(
                    requestor=assets_request.requesting_user.username, request_id=assets_request.pk
                ),
                "modal": "assets-confirm-request",
                "icon": "fas fa-trash",
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
                "title": _("Confirm Request"),
                "text": _("Confirm Request for {requestor} - ID: {request_id}").format(
                    requestor=assets_request.requesting_user.username, request_id=assets_request.pk
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
                    "title": _("Reopen Request"),
                    "text": _("Reopen Request for {requestor} - ID: {request_id}").format(
                        requestor=assets_request.requesting_user.username, request_id=assets_request.pk
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