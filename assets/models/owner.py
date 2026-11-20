"""Owner model: a character or corporation whose assets are synced from ESI."""

# Django
from django.db import models, transaction

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from esi.errors import TokenError
from esi.models import Token

# Alliance Auth (External Libs)
from eve_sde.models.types import ItemType

# AA Assets
from assets import contexts
from assets.managers.assets import get_market_price
from assets.managers.owner import OwnerManager, OwnerUpdateStatusManager
from assets.models.assets import Assets
from assets.models.helpers.update_manager import (
    OwnerUpdateSection,
    UpdateManagerMixin,
    UpdateSectionResult,
    UpdateStatusBaseModel,
)
from assets.models.location import Location
from assets.models.request import Request, RequestAssets
from assets.providers import logger


def get_or_create_location(location_id: int) -> "Location":
    """Get or create a location sync - helper function."""
    obj, _ = Location.objects.get_or_create_esi(location_id=location_id)
    return obj


class Owner(UpdateManagerMixin, models.Model):
    """A model defining an owner of assets."""

    update_section_class = OwnerUpdateSection
    update_status_model = "OwnerUpdateStatus"  # set below, after the class exists

    corporation = models.OneToOneField(
        EveCorporationInfo,
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Corporation used for syncing",
        related_name="+",
    )
    character = models.ForeignKey(
        CharacterOwnership,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        help_text="character used for syncing",
        related_name="+",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=("whether this owner is currently included in the sync process"),
    )

    objects = OwnerManager()

    class Meta:
        default_permissions = ()

    def __str__(self) -> str:
        if self.corporation:
            return f"{self.corporation.corporation_name} (Corp)"
        if self.character and self.character.character:
            return f"{self.character.character.character_name} (Char)"
        return f"Owner #{self.pk} (No Corp/Char)"

    @property
    def active(self) -> bool:
        """Return `is_active`, the name `UpdateManagerMixin.get_status` reads."""
        return self.is_active

    @property
    def name(self) -> str:
        """Return the name of this owner."""
        try:
            if self.corporation:
                return self.corporation.corporation_name
            return self.eve_character_strict.character_name
        except (ValueError, AttributeError):
            return ""

    @property
    def corporation_strict(self) -> EveCorporationInfo:
        """Return corporation of this owner when it exists, or raises error."""
        if not self.corporation:
            raise ValueError("No corporation defined")
        return self.corporation

    @property
    def eve_character_strict(self) -> EveCharacter:
        """Return character of this owner when it exists, or raises error."""
        if not self.character or not self.character.character:
            raise ValueError("No character defined")
        return self.character.character

    def get_esi_scopes(self) -> list[str]:
        """Return the required ESI scopes for this owner."""
        if self.corporation:
            return [
                "esi-universe.read_structures.v1",
                "esi-assets.read_corporation_assets.v1",
            ]
        return ["esi-universe.read_structures.v1", "esi-assets.read_assets.v1"]

    def process_assets(self, assets: list[contexts.GetAssetsContext]):
        items = []
        item_ids = list(
            {
                asset.type_id
                for asset in assets
                if get_market_price(asset.type_id) is None
            }
        )

        if item_ids:
            # Update or create prices for all items and save them in cache
            Assets.objects.update_or_create_prices(item_ids)

        for asset in assets:
            try:
                price = float(get_market_price(asset.type_id))
            except AttributeError:
                price = None

            location_flag = Assets.LocationFlag.from_esi_data(asset.location_flag)
            eve_type = ItemType.objects.get(id=asset.type_id)
            asset_item = Assets(
                location=get_or_create_location(asset.location_id),
                location_flag=location_flag,
                location_type=asset.location_type,
                eve_type=eve_type,
                item_id=asset.type_id,
                quantity=asset.quantity,
                singleton=asset.is_singleton,
                blueprint_copy=asset.is_blueprint_copy,
                owner=self,
                price=price,
            )
            items.append(asset_item)
        return items

    def replace_assets(self, items: list[Assets]) -> None:
        """Replace all assets of this owner and relink its open orders."""
        with transaction.atomic():
            orders = self.get_open_orders()
            self.flush_assets()
            Assets.objects.bulk_create(items)
            self.update_order_assets(orders)

    def get_open_orders(self) -> list[RequestAssets]:
        """Return the open orders of assets of this owner."""
        return list(
            RequestAssets.objects.filter(
                request__status=Request.STATUS_OPEN,
                asset_pk__in=Assets.objects.filter(owner=self).values("pk"),
            )
        )

    def update_order_assets(self, orders: list[RequestAssets]) -> None:
        """Link the given orders to the matching current assets of this owner."""
        orders_to_update = []
        for order in orders:
            asset = (
                Assets.objects.filter(
                    owner=self,
                    eve_type=order.eve_type,
                    location_id=order.asset_location_id,
                    location_flag=order.asset_location_flag,
                )
                .order_by("pk")
                .first()
            )
            if asset is None:
                continue
            order.asset_pk = asset.pk
            orders_to_update.append(order)

        if orders_to_update:
            logger.info("Updated %s orders for %s", len(orders_to_update), self.name)
            RequestAssets.objects.bulk_update(orders_to_update, ["asset_pk"])

    # Task Area: one `update_<section>` method per OwnerUpdateSection
    def update_assets(self, force_refresh: bool = False) -> UpdateSectionResult:
        """Update the assets of this owner."""
        return Owner.objects.update_assets_esi(self, force_refresh=force_refresh)

    def valid_token(self, scopes) -> Token:
        """Return a valid token for the owner or raise exception."""

        token = (
            Token.objects.filter(
                user=self.character.user,
                character_id=self.eve_character_strict.character_id,
            )
            .require_scopes(scopes)
            .require_valid()
            .first()
        )
        if not token:
            raise TokenError(f"{self}: No valid token found")

        return token

    def flush_assets(self):
        """Delete all assets for this owner."""
        delete_query = Assets.objects.filter(owner=self)  # Flush Assets
        if delete_query.exists():
            delete_query._raw_delete(delete_query.db)


class OwnerUpdateStatus(UpdateStatusBaseModel):
    """The update status of one section of an Owner."""

    class Meta(UpdateStatusBaseModel.Meta):
        default_permissions = ()

    objects: OwnerUpdateStatusManager = OwnerUpdateStatusManager()

    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name="assets_update_status",
    )
    section = models.CharField(
        max_length=32, choices=OwnerUpdateSection.choices, db_index=True
    )


Owner.update_status_model = OwnerUpdateStatus
