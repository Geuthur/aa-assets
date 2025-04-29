from typing import List, Any

from ninja import NinjaAPI

from django.utils import timezone
from django.core.handlers.wsgi import WSGIRequest

from assets.api import schema
from assets.hooks import get_extension_logger
from assets.models import Request
from assets.api.requests.helper import _request_actions

logger = get_extension_logger(__name__)


class RequestsApiEndpoints:
    tags = ["Requests"]

    def __init__(self, api: NinjaAPI):       
        @api.get(
            "requests/",
            response={200: List[schema.Requests], 403: str},
            tags=self.tags,
        )
        def get_open_requests(request: WSGIRequest):
            perms = request.user.has_perm("assets.manage_requests")

            if not perms:
                return 403, "Permission Denied"

            requests_data = Request.objects.all()

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
                        "order": "",
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
                        "actions": _request_actions(
                            req,
                            perms,
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
            perms = request.user.has_perm("assets.basic_access")

            if not perms:
                return 403, "Permission Denied"

            requests_data = Request.objects.filter(requesting_user=request.user)

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
                        "order": "",
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
                        "actions": _request_actions(
                            req,
                            perms,
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