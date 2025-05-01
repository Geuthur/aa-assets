from django.core.exceptions import ObjectDoesNotExist
from django.template.loader import render_to_string
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

from allianceauth.eveonline.models import EveCharacter

from assets.hooks import get_extension_logger
from assets.models import Request

logger = get_extension_logger(__name__)


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


def get_manage_permission(request) -> bool:
    """Get Permission for Corporation"""
    perms = True
    character_id = request.user.profile.main_character.character_id

    try:
        main_char = EveCharacter.objects.get(character_id=character_id)
    except ObjectDoesNotExist:
        return False
    except ValueError:
        return False

    # Check access
    visible = Request.objects.manage_eve_characters(request.user)

    if main_char not in visible:
        perms = False
    return perms


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
