# Django
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# AA Assets
from assets.hooks import get_extension_logger
from assets.models import Assets, Request, RequestAssets

logger = get_extension_logger(__name__)


def update_asset_object(asset: Assets) -> Assets | bool:
    """Update the asset object based on open requests."""
    req_assets = RequestAssets.objects.filter(asset_pk=asset.pk)

    # Filter out requests that are completed and not older than 2 hours
    recent_ordered_quantity = req_assets.filter(
        request__status=Request.STATUS_COMPLETED,
        request__closed_at__gte=timezone.now() - timezone.timedelta(hours=2),
    ).aggregate(total_quantity=Sum("quantity"))["total_quantity"]

    ordered_quantity = req_assets.filter(
        request__status=Request.STATUS_OPEN,
    ).aggregate(total_quantity=Sum("quantity"))["total_quantity"]

    if recent_ordered_quantity:
        if recent_ordered_quantity >= asset.quantity:
            return False
        asset.quantity -= recent_ordered_quantity

    if ordered_quantity:
        if ordered_quantity >= asset.quantity:
            return False
        asset.quantity -= ordered_quantity

    return asset
