from typing import List

from ninja import NinjaAPI

from assets.api import schema
from assets.hooks import get_extension_logger
from assets.models import Request

logger = get_extension_logger(__name__)


class RequestsApiEndpoints:
    tags = ["Assets"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "requests/",
            response={200: List[schema.Requests], 403: str},
            tags=self.tags,
            auth=None,
        )
        def get_open_requests(request):
            perms = request.user.has_perm("assets.manage_requests")

            if not perms:
                return 403, "Permission Denied"

            requests_data = Request.objects.all()
            requests_data = Request.objects.exclude(status=Request.STATUS_COMPLETED)

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
