"""PvE Views"""

# Standard Library
from http import HTTPStatus

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

# Alliance Auth
from allianceauth.authentication.decorators import permissions_required
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCorporationInfo
from esi.decorators import token_required

# AA Assets
from assets import forms
from assets.helpers.admin import queue_admin_tasks
from assets.helpers.orders import (
    MODE_CANCELED,
    MODE_COMPLETED,
    MODE_OPEN,
    change_request_status,
    cooldown_message,
    exceeds_message,
    get_apr_cooldown,
)
from assets.helpers.orders import create_order as create_order_for_user
from assets.hooks import add_info_to_context
from assets.models import Assets, Owner, Request
from assets.tasks import update_assets_for_owner


@login_required
@permissions_required(["assets.basic_access"])
def index(request):
    context = {
        "corporation_id": request.user.profile.main_character.corporation_id,
        "title": _("Assets"),
    }
    context = add_info_to_context(request, context)

    return render(request, "assets/index.html", context=context)


@login_required
@permissions_required(["assets.basic_access"])
def admin(request):
    if not request.user.is_superuser:
        messages.error(request, _("You do not have permission to access this page."))
        return redirect("assets:index")

    if request.method == "POST":
        queued = queue_admin_tasks(
            force_refresh=bool(request.POST.get("force_refresh", False)),
            clear_etags=bool(request.POST.get("run_clear_etag")),
            update_assets=bool(request.POST.get("run_update_all_assets")),
            update_locations=bool(request.POST.get("run_update_all_locations")),
            update_parent_locations=bool(
                request.POST.get("run_update_all_parent_locations")
            ),
        )
        for msg in queued:
            messages.info(request, msg)
    return render(request, "assets/admin.html")


@login_required
@permissions_required(["assets.basic_access"])
def location(request):
    context = {
        "corporation_id": request.user.profile.main_character.corporation_id,
        "character_id": request.user.profile.main_character.character_id,
        "title": _("Locations"),
    }
    context = add_info_to_context(request, context)

    return render(request, "assets/location.html", context=context)


@login_required
@permissions_required(["assets.basic_access"])
def assets(request, location_id: int, location_flag: str):
    context = {
        "corporation_id": request.user.profile.main_character.corporation_id,
        "character_id": request.user.profile.main_character.character_id,
        "title": _("Assets"),
        "location_id": location_id,
        "location_flag": location_flag,
        "forms": {
            "single_request": forms.RequestOrder(),
            "multi_request": forms.RequestMultiOrder(
                location_flag=location_flag, location_id=location_id
            ),
        },
    }
    context = add_info_to_context(request, context)

    return render(request, "assets/assets.html", context=context)


@login_required
@permissions_required(["assets.basic_access"])
def requests(request):
    context = {
        "corporation_id": request.user.profile.main_character.corporation_id,
        "character_id": request.user.profile.main_character.character_id,
        "title": _("Manage Requests"),
    }
    context = add_info_to_context(request, context)

    return render(request, "assets/requests.html", context=context)


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


@login_required
@permissions_required(["assets.basic_access"])
@require_POST
def create_order(request, location_id: int, location_flag: str):
    """Render view to create a new order request."""
    # Check Permission
    form = forms.RequestOrder(request.POST)
    form_multi = forms.RequestMultiOrder(
        request.POST, location_flag=location_flag, location_id=location_id
    )

    if form.is_valid():
        amount = int(form.cleaned_data["amount"])
        asset_pk = request.POST.get("asset_pk")

        try:
            asset = Assets.objects.visible_to(request.user).get(pk=asset_pk)
        except Assets.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "The asset does not exist."},
                status=HTTPStatus.NOT_FOUND,
                safe=False,
            )

        user_request, _exceeds = create_order_for_user(request.user, [(asset, amount)])
        if user_request is None:
            return JsonResponse(
                {
                    "success": False,
                    "message": _("Requested amount exceeds available quantity."),
                },
                status=HTTPStatus.FORBIDDEN,
                safe=False,
            )
        return JsonResponse(
            {"success": True, "message": "Order created successfully."},
            status=HTTPStatus.OK,
            safe=False,
        )

    if form_multi.is_valid():
        cleaned_data = form_multi.cleaned_data
        asset_data = [
            (int(key.split("_")[2]), cleaned_data[key])
            for key in cleaned_data.keys()
            if key.startswith("item_id_")
        ]

        items = []
        for asset_pk, amount in asset_data:
            if amount is None:
                continue

            try:
                asset = Assets.objects.visible_to(request.user).get(pk=asset_pk)
            except Assets.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "The asset does not exist."},
                    status=HTTPStatus.NOT_FOUND,
                    safe=False,
                )
            items.append((asset, amount))

        _user_request, exceeds_items = create_order_for_user(request.user, items)

        if exceeds_items:
            return JsonResponse(
                {"success": False, "message": exceeds_message(exceeds_items)},
                status=HTTPStatus.CONFLICT,
                safe=False,
            )
        return JsonResponse(
            {"success": True, "message": "Order created successfully."},
            status=HTTPStatus.OK,
            safe=False,
        )

    return JsonResponse(
        {"success": True, "message": "Invalid Form"},
        status=HTTPStatus.NOT_FOUND,
        safe=False,
    )


def _mark_request(request, request_id: int, mode: str, cooldown_success: bool):
    """Answer a status change of an order like the views always did."""
    if get_apr_cooldown(request.user, request_id, mode):
        return JsonResponse(
            {"success": cooldown_success, "message": cooldown_message()},
            status=HTTPStatus.FORBIDDEN,
            safe=False,
        )

    user_request = get_object_or_404(Request, pk=request_id)
    is_changed, msg = change_request_status(request.user, user_request, mode)
    return JsonResponse(
        {"success": is_changed, "message": msg},
        status=HTTPStatus.OK if is_changed else HTTPStatus.BAD_REQUEST,
        safe=False,
    )


@login_required
@permissions_required(["assets.basic_access"])
@require_POST
def mark_request_canceled(request, request_id: int):
    """Render view to mark a order request as canceled."""
    return _mark_request(request, request_id, MODE_CANCELED, cooldown_success=True)


@login_required
@permissions_required(["assets.basic_access"])
@permissions_required(["assets.manage_requests"])
@require_POST
def mark_request_completed(request, request_id: int):
    """Render view to mark a order request as completed."""
    return _mark_request(request, request_id, MODE_COMPLETED, cooldown_success=False)


@login_required
@permissions_required(["assets.basic_access"])
@permissions_required(["assets.manage_requests"])
@require_POST
def mark_request_open(request, request_id: int):
    """Render view to mark a order request as open."""
    return _mark_request(request, request_id, MODE_OPEN, cooldown_success=True)
