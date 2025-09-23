# Standard Library
from typing import Any

# Third Party
from ninja import NinjaAPI

# Django
from django.urls import reverse
from django.utils.html import format_html

# AA Assets
from assets.api import schema
from assets.api.assets.helper import update_asset_object
from assets.api.helpers import get_asset, get_owner
from assets.constants import STANDARD_FLAG
from assets.hooks import get_extension_logger
from assets.models import Assets, Location

logger = get_extension_logger(__name__)


class AssetsApiEndpoints:
    tags = ["Assets"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "location/{location_id}/flag/{location_flag}/",
            response={200: schema.Assets, 403: str},
            tags=self.tags,
            auth=None,
        )
        def get_assets(request, location_id: int, location_flag):
            perms, asset_obj = get_asset(request, location_id)

            if not perms:
                return 403, "Permission Denied"

            # Store original location_flag for response
            response_location_flag = location_flag

            # Set default location_flag if not provided
            if location_flag == "all":
                location_flag = STANDARD_FLAG
            else:
                location_flag = [location_flag]

            assets_qs = (
                asset_obj.filter(location_flag__in=location_flag)
                .select_related("location", "eve_type")
                .annotate_location_name()
            )
            assets = []

            for asset in assets_qs:
                asset = update_asset_object(asset)

                if asset is False:
                    continue

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
                        "location": asset.location_name,
                        "location_flag": asset.get_location_flag_display(),
                        "price": price,
                    }
                )

            output = {
                "location_id": location_id,
                "location_flag": response_location_flag,
                "assets": assets,
            }

            return output

        @api.get(
            "location/",
            response={200: Any, 403: str},
            tags=self.tags,
            auth=None,
        )
        def get_locations(request):
            """
            Get all locations for the user.
            """

            perm, owner = get_owner(request)
            if not perm:
                return 403, "Permission Denied"

            locations_ids = (
                Assets.objects.filter(
                    owner__in=owner,
                    location_flag__in=STANDARD_FLAG,
                )
                .values_list("location_id", flat=True)
                .distinct()
            )

            locations = (
                Location.objects.filter(id__in=locations_ids)
                .select_related("eve_solar_system", "eve_type", "parent")
                .distinct()
                .annotate_location_name()
                .annotate_system_name()
            )

            output = []

            for location in locations:
                url = reverse(
                    viewname="assets:assets",
                    kwargs={"location_id": location.id, "location_flag": "all"},
                )
                html = f"<a href='{url}'><button class='btn btn-primary'>View Assets</button></a>"

                output.append(
                    {
                        "location_id": location.id,
                        "name": location.location_name,
                        "solar_system": location.system_name,
                        "view": format_html(html),
                    }
                )

            return output
