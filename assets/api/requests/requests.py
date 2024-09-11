from typing import List

from ninja import NinjaAPI

from django.utils import timezone

from assets.api import schema
from assets.hooks import get_extension_logger
from assets.models import Request

logger = get_extension_logger(__name__)


class RequestsApiEndpoints:
    tags = ["Requests"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "requests/",
            response={200: List[schema.Requests], 403: str},
            tags=self.tags,
        )
        def get_open_requests(request):
            perms = request.user.has_perm("assets.manage_requests")

            if not perms:
                return 403, "Permission Denied"

            requests_data = Request.objects.all()

            skip_old_entrys = timezone.now() - timezone.timedelta(days=3)

            # Skip old entries older then 3 days
            requests_data = requests_data.exclude(
                status=Request.STATUS_CANCELLED, closed_at__lt=skip_old_entrys
            )
            # Skip completed entries
            requests_data = requests_data.exclude(status=Request.STATUS_COMPLETED)

            output = []

            for req in requests_data:
                output.append(
                    {
                        "id": req.pk,
                        "order": req.order,
                        "status": req.get_status_display(),
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
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

            requests_data = requests_data.exclude(status__in=[Request.STATUS_COMPLETED])

            output = []

            for req in requests_data:
                output.append(
                    {
                        "id": req.pk,
                        "order": req.order,
                        "status": req.get_status_display(),
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
                    }
                )

            return output
