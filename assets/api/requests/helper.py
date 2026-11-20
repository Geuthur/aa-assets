# AA Assets
from assets.managers import GeneralManager
from assets.models import Request


def request_permissions(assets_request: Request, user) -> dict[str, bool]:
    """Which status changes the user may make on this order."""
    manager = GeneralManager.has_manage_requests_access(user)
    is_open = assets_request.status == Request.STATUS_OPEN
    return {
        "can_cancel": is_open
        and (manager or assets_request.requesting_user_id == user.pk),
        "can_complete": is_open and manager,
        "can_reopen": assets_request.status == Request.STATUS_CANCELLED and manager,
    }
