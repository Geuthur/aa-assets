from typing import List

from ninja import NinjaAPI

from assets.api import schema
from assets.hooks import get_extension_logger
from assets.models import Assets

logger = get_extension_logger(__name__)


class AssetsApiEndpoints:
    tags = ["Assets"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "assets/filter/{location}/",
            response={200: List[schema.Assets], 403: str},
            tags=self.tags,
            auth=None,
        )
        def get_assets(request, location: str):
            perms = request.user.has_perm("assets.basic_access")

            if not perms:
                return 403, "Permission Denied"

            assets = Assets.objects.all().select_related("location", "eve_type")
            assets = assets.filter(location_flag=location, location_id=1042478386825)

            output = []

            for asset in assets:
                try:
                    price = asset.price * asset.quantity
                except TypeError:
                    price = "N/A"
                output.append(
                    {
                        "item_id": asset.item_id,
                        "name": asset.eve_type.name,
                        "quantity": asset.quantity,
                        "location": (
                            asset.location.parent.name
                            if asset.location.parent
                            else "N/A"
                        ),
                        "price": price,
                    }
                )

            return output
