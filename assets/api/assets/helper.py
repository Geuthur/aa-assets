from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from assets.models import Assets, Request, RequestAssets


def update_asset_object(asset: Assets) -> Assets | bool:
    """Update the asset object based on open requests."""
    req_assets = RequestAssets.objects.filter(asset=asset)

    # Filter out requests that are completed and not older than 2 hours
    recent_completed_requests = req_assets.filter(
        requestor__status=Request.STATUS_COMPLETED,
        requestor__closed_at__gte=timezone.now() - timezone.timedelta(hours=2),
    )

    if recent_completed_requests.exists():
        return False

    ordered_quantity = req_assets.filter(
        requestor__status=Request.STATUS_OPEN,
    ).aggregate(total_quantity=Sum("quantity"))["total_quantity"]

    if ordered_quantity:
        if ordered_quantity >= asset.quantity:
            return False
        asset.quantity -= ordered_quantity

    return asset
