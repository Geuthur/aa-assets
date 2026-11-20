"""Views: the React entry point and the SSO steps to add characters and corporations."""

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

# Alliance Auth
from allianceauth.authentication.decorators import permissions_required
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCorporationInfo
from esi.decorators import token_required

# AA Assets
from assets import __app_name__, __version__
from assets.models import Owner
from assets.tasks import update_assets_for_owner


@login_required
@permissions_required(["assets.basic_access"])
def react_base(request: WSGIRequest):
    """Serve the React app; routing and permissions of the pages are handled by the API."""
    context = {"version": __version__, "app_name": __app_name__}
    return render(request, "assets/react_base.html", context=context)


@login_required
@permissions_required(["assets.basic_access"])
@permissions_required(["assets.manage_corporation"])
@token_required(
    scopes=["esi-universe.read_structures.v1", "esi-assets.read_corporation_assets.v1"]
)
def add_corp(request, token) -> HttpResponse:
    char = get_object_or_404(
        CharacterOwnership, character__character_id=token.character_id
    )
    corp, _ = EveCorporationInfo.objects.get_or_create(
        corporation_id=char.character.corporation_id,
        defaults={
            "member_count": 0,
            "corporation_ticker": char.character.corporation_ticker,
            "corporation_name": char.character.corporation_name,
        },
    )

    owner, _ = Owner.objects.update_or_create(character=char, corporation=corp)

    update_assets_for_owner.apply_async(
        args=[owner.pk], kwargs={"force_refresh": True}, priority=6
    )
    msg = f"{owner.name} successfully added/updated to Assets"
    messages.info(request, msg)
    return redirect("assets:index")


@login_required
@permissions_required(["assets.basic_access"])
@token_required(scopes=["esi-universe.read_structures.v1", "esi-assets.read_assets.v1"])
def add_char(request, token) -> HttpResponse:
    char = get_object_or_404(
        CharacterOwnership, character__character_id=token.character_id
    )
    owner, _ = Owner.objects.update_or_create(
        corporation=None,
        character=char,
    )

    update_assets_for_owner.apply_async(
        args=[owner.pk], kwargs={"force_refresh": True}, priority=6
    )
    msg = f"{owner.name} successfully added/updated to Assets"
    messages.info(request, msg)
    return redirect("assets:index")
