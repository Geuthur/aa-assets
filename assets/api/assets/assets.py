from ninja import NinjaAPI

from django.db.models import Sum

from assets.api import schema
from assets.hooks import get_extension_logger
from assets.models import Assets, Request, RequestAssets

logger = get_extension_logger(__name__)


class AssetsApiEndpoints:
    tags = ["Assets"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "assets/location/{location_id}/{location_flag}/",
            response={200: schema.Assets, 403: str},
            tags=self.tags,
            auth=None,
        )
        def get_assets(request, location_id: int, location_flag: str):
            perms = request.user.has_perm("assets.basic_access")

            if not perms:
                return 403, "Permission Denied"

            assets_qs = Assets.objects.all().select_related("location", "eve_type")
            assets_qs = assets_qs.filter(
                location_flag=location_flag, location_id=location_id
            )

            assets = []

            for asset in assets_qs:
                ordered_quantity = RequestAssets.objects.filter(
                    asset=asset,
                    requestor__status=Request.STATUS_OPEN,
                ).aggregate(total_quantity=Sum("quantity"))["total_quantity"]

                if ordered_quantity:
                    if ordered_quantity >= asset.quantity:
                        continue
                    asset.quantity -= ordered_quantity

                try:
                    price = asset.price * asset.quantity
                except TypeError:
                    price = "N/A"
                assets.append(
                    {
                        "asset_pk": asset.pk,
                        "item_id": asset.item_id,
                        "name": asset.eve_type.name,
                        "quantity": asset.quantity,
                        "location_id": asset.location.id,
                        "location": (
                            asset.location.parent.name
                            if asset.location.parent
                            else "N/A"
                        ),
                        "price": price,
                    }
                )

            output = {
                "location_id": location_id,
                "location_flag": location_flag,
                "assets": assets,
            }

            return output
