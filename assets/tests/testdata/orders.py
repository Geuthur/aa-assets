"""Owners, assets and orders for the order tests."""

# AA EVE SDE Factory
# Third Party
from evesde_factory.eve_sde import ItemTypeFactory

# AA Assets
from assets.models import Assets, Location, Owner, Request, RequestAssets

LOCATION_ID = 60003760


def create_owner(user) -> Owner:
    """Character owner of the user's main character."""
    return Owner.objects.create(
        character=user.profile.main_character.character_ownership
    )


def create_asset(owner: Owner, quantity: int = 10, item_id: int = 1) -> Assets:
    """One asset of the owner in a station hangar."""
    location, _ = Location.objects.get_or_create(
        id=LOCATION_ID, defaults={"name": "Jita IV - Moon 4"}
    )
    return Assets.objects.create(
        item_id=item_id,
        owner=owner,
        eve_type=ItemTypeFactory(),
        location=location,
        location_flag=Assets.LocationFlag.HANGAR,
        location_type="station",
        quantity=quantity,
        singleton=False,
        blueprint_copy=False,
    )


def create_order(
    user, asset: Assets, quantity: int = 1, status: str = Request.STATUS_OPEN
) -> Request:
    """An order of the user for one asset."""
    order = Request.objects.create(requesting_user=user, status=status)
    RequestAssets.objects.create(
        name=asset.eve_type.name,
        request=order,
        asset_pk=asset.pk,
        asset_location_id=asset.location.id,
        asset_location_flag=asset.location_flag,
        eve_type=asset.eve_type,
        quantity=quantity,
    )
    return order
