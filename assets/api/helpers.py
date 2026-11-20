# Django
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

# Alliance Auth
from allianceauth.eveonline.models import EveCharacter

# AA Assets
from assets.models import Assets, Owner, Request


def generate_button(template, queryset, settings, request) -> mark_safe:
    """Generate a html button for the tax system"""
    return format_html(
        render_to_string(
            template,
            {
                "queryset": queryset,
                "settings": settings,
            },
            request=request,
        )
    )


def get_character_permission(request) -> bool:
    """Get Character and check permissions"""
    perms = True
    character_id = request.user.profile.main_character.character_id

    try:
        main_char = EveCharacter.objects.get(character_id=character_id)
    except ObjectDoesNotExist:
        return False
    except ValueError:
        return False

    # check access
    visible = Request.objects.visible_eve_characters(request.user)
    if main_char not in visible:
        perms = False
    return perms


def get_manage_permission(request) -> bool:
    """Get Permission for Corporation"""
    perms = True
    owner = Owner.objects.all()

    # Check access
    visible = Owner.objects.manage_to(request.user)

    # Check if there is an intersection between owner and visible
    if not owner.intersection(visible).exists():
        perms = False

    return perms


def get_asset(request, location_id: int) -> tuple[bool, QuerySet[Assets]]:
    """Get the assets in the location that the request user may see."""
    asset = Assets.objects.visible_to(request.user).filter(location_id=location_id)
    return asset.exists(), asset


def get_owner(request) -> tuple[bool, QuerySet[Owner]]:
    """Get the owners that the request user may see."""
    owner = Owner.objects.visible_to(request.user)
    return owner.exists(), owner
