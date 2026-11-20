# Django
from django.db.models import QuerySet

# AA Assets
from assets.models import Assets, Owner


def get_asset(request, location_id: int) -> tuple[bool, QuerySet[Assets]]:
    """Get the assets in the location that the request user may see."""
    asset = Assets.objects.visible_to(request.user).filter(location_id=location_id)
    return asset.exists(), asset


def get_owner(request) -> tuple[bool, QuerySet[Owner]]:
    """Get the owners that the request user may see."""
    owner = Owner.objects.visible_to(request.user)
    return owner.exists(), owner
