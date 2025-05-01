from typing import Any, List

from ninja import NinjaAPI

from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from assets.api import schema
from assets.api.helpers import get_character_permission, get_manage_permission
from assets.api.requests.helper import (
    _my_request_actions,
    _request_actions,
    _request_list,
)
from assets.hooks import get_extension_logger
from assets.models import Request, RequestAssets

logger = get_extension_logger(__name__)


class RequestsApiEndpoints:
    tags = ["Requests"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "requests/",
            response={200: List[schema.Requests], 403: str},
            tags=self.tags,
        )
        def get_requests(request: WSGIRequest):
            requests_data = Request.objects.visible_to(request.user)

            if requests_data is None:
                return 403, "Permission Denied"

            perm = get_character_permission(request)
            admin = get_manage_permission(request)

            skip_old_entrys = timezone.now() - timezone.timedelta(days=3)

            # Skip old entries older then 3 days
            requests_data = requests_data.exclude(
                status=Request.STATUS_CANCELLED, closed_at__lt=skip_old_entrys
            )

            requests_data = requests_data.exclude(
                status=Request.STATUS_COMPLETED, closed_at__lt=skip_old_entrys
            )

            output = []

            for req in requests_data:
                output.append(
                    {
                        "id": req.pk,
                        "status": req.get_status_display(),
                        "order": _request_list(
                            req,
                            perm,
                            request,
                        ),
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
                        "actions": _request_actions(
                            req,
                            admin,
                            request,
                        ),
                    }
                )

            return output

        @api.get(
            "requests/myrequests/",
            response={200: List[schema.Requests], 403: str},
            tags=self.tags,
        )
        def get_my_requests(request):
            requests_data = Request.objects.visible_to(request.user)

            if requests_data is None:
                return 403, "Permission Denied"

            requests_data = requests_data.filter(requesting_user=request.user)

            perm = get_character_permission(request)
            admin = get_manage_permission(request)

            skip_old_entrys = timezone.now() - timezone.timedelta(days=3)

            # Skip old entries older then 3 days
            requests_data = requests_data.exclude(
                status=Request.STATUS_CANCELLED, closed_at__lt=skip_old_entrys
            )

            output = []

            for req in requests_data:
                output.append(
                    {
                        "id": req.pk,
                        "status": req.get_status_display(),
                        "order": _request_list(
                            req,
                            perm,
                            request,
                        ),
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
                        "actions": _my_request_actions(
                            req,
                            admin,
                            request,
                        ),
                    }
                )

            return output

        @api.get(
            "requests/statistics/",
            response={200: Any, 403: str},
            tags=self.tags,
        )
        def get_requests_statistics(request: WSGIRequest):
            perms = request.user.has_perm("assets.basic_access")

            if not perms:
                return 403, "Permission Denied"

            if request.user.has_perm("assets.manage_requests"):
                requests_count = Request.objects.open_requests_total_count()
            else:
                requests_count = None

            my_requests_count = Request.objects.my_requests_total_count(request.user)

            output = {
                "requestCount": requests_count,
                "myRequestCount": my_requests_count,
            }

            return output

        @api.get(
            "requests/order/{request_id}/",
            response={200: Any, 403: str},
            tags=self.tags,
        )
        def get_request_order(request: WSGIRequest, request_id: int):
            """Get the order for a request"""
            perms = request.user.has_perm("assets.basic_access")

            if not perms:
                return 403, "Permission Denied"

            try:
                request_user = Request.objects.get(
                    pk=request_id,
                )
            except Request.DoesNotExist:
                return 403, "Request does not exist"

            orders = RequestAssets.objects.filter(
                request__pk=request_id,
            )

            output = []

            for order in orders:
                output.append(
                    {
                        "item_id": order.eve_type.id,
                        "name": order.eve_type.name,
                        "quantity": order.quantity,
                    }
                )

            context = {
                "request_id": request_id,
                "orders": output,
                "title": _("Order for {requestor} - ID: {request_id}").format(
                    requestor=request_user.requesting_user.username,
                    request_id=request_id,
                ),
            }

            return render(request, "assets/partials/modal/view-order.html", context)
