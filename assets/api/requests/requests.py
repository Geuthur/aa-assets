# Third Party
from ninja import NinjaAPI

# Django
from django.core.handlers.wsgi import WSGIRequest
from django.utils import timezone

# AA Assets
from assets.api import schema
from assets.api.requests.helper import request_permissions
from assets.models import Request


class RequestsApiEndpoints:
    tags = ["Requests"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "requests/",
            response={200: list[schema.Requests], 403: schema.ErrorSchema},
            tags=self.tags,
        )
        def get_requests(request: WSGIRequest):
            requests_data = Request.objects.visible_to(request.user)

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
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
                        **request_permissions(req, request.user),
                    }
                )

            return output

        @api.get(
            "requests/myrequests/",
            response={200: list[schema.Requests], 403: schema.ErrorSchema},
            tags=self.tags,
        )
        def get_my_requests(request):
            requests_data = Request.objects.visible_to(request.user)

            requests_data = requests_data.filter(requesting_user=request.user)

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
                        "action": req.status,
                        "created": req.created_at,
                        "closed": req.closed_at,
                        "approver": (
                            req.approver_user.username if req.approver_user else None
                        ),
                        "requestor": req.requesting_user.username,
                        **request_permissions(req, request.user),
                    }
                )

            return output
