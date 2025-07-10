"""PvE Views"""

from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction

# Django
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from esi.decorators import token_required

from allianceauth.authentication.decorators import permissions_required
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCorporationInfo

from assets import forms
from assets.hooks import add_info_to_context, get_extension_logger
from assets.models import Assets, Owner, Request, RequestAssets
from assets.tasks import update_assets_for_owner

logger = get_extension_logger(__name__)


def build_apr_cooldown_cache_tag(user, request_id, mode):
    return f"cooldown_request_{user}_{request_id}_{mode}"


def get_apr_cooldown(request, request_id, mode):
    if cache.get(build_apr_cooldown_cache_tag(request.user, request_id, mode), False):
        return True
    return False


def set_apr_cooldown(user, request_id, mode):
    """Set a 60 sec cooldown forthe Approver"""
    return cache.set(build_apr_cooldown_cache_tag(user, request_id, mode), True, (60))


def validate_asset_quantity(asset: Assets, amount: int) -> tuple[bool, str]:
    """Validates if the requested amount exceeds the available quantity."""
    requests_obj = RequestAssets.objects.filter(
        asset_pk=asset.pk,
        eve_type=asset.eve_type,
        request__status=Request.STATUS_OPEN,
    ).values_list("quantity", flat=True)
    if requests_obj and sum(requests_obj) + amount > asset.quantity:
        return False
    return True


def create_request_asset_object(
    user_request: Request, asset: Assets, amount: int
) -> RequestAssets:
    """Create a RequestAssets Object."""
    return RequestAssets(
        name=asset.eve_type.name,
        request=user_request,
        asset_pk=asset.pk,
        asset_location_id=asset.location.id,
        asset_location_flag=asset.location_flag,
        eve_type=asset.eve_type,
        quantity=amount,
    )


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
@token_required(
    scopes=["esi-universe.read_structures.v1", "esi-assets.read_corporation_assets.v1"]
)
@permissions_required(["assets.add_corporate_owner"])
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
@token_required(scopes=["esi-universe.read_structures.v1", "esi-assets.read_assets.v1"])
@permissions_required(["assets.add_character_owner"])
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
        user = request.user

        try:
            asset = Assets.objects.get(pk=asset_pk)
        except Assets.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "The asset does not exist."},
                status=HTTPStatus.NOT_FOUND,
                safe=False,
            )

        is_valid = validate_asset_quantity(asset, amount)
        if not is_valid:
            return JsonResponse(
                {
                    "success": False,
                    "message": _("Requested amount exceeds available quantity."),
                },
                status=HTTPStatus.FORBIDDEN,
                safe=False,
            )

        # Create Request object
        user_request = Request(
            requesting_user=user,
            status=Request.STATUS_OPEN,
        )

        # Create RequestAssets object
        # and save it to the database
        with transaction.atomic():
            asset_request = create_request_asset_object(user_request, asset, amount)
            user_request.save()
            asset_request.save()
            user_request.notify_new_request()
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

        user = request.user

        # Create Request object
        user_request = Request(
            requesting_user=user,
            status=Request.STATUS_OPEN,
        )

        exceeds_items = []
        assets_items = []
        for asset_pk, amount in asset_data:
            if amount is None:
                continue

            try:
                asset = Assets.objects.get(pk=asset_pk)
            except Assets.DoesNotExist:
                return JsonResponse(
                    {"success": False, "message": "The asset does not exist."},
                    status=HTTPStatus.NOT_FOUND,
                    safe=False,
                )

            is_valid = validate_asset_quantity(asset, amount)
            if is_valid:
                assets_items.append(
                    create_request_asset_object(user_request, asset, amount)
                )
            else:
                exceeds_items.append(asset.eve_type.name)

        if assets_items:
            with transaction.atomic():
                user_request.save()
                for asset_request in assets_items:
                    asset_request.save()
                user_request.notify_new_request()

        if exceeds_items:
            error_message = f"The following items exceeds the available quantity {', '.join(exceeds_items)} and are not included in your order."
            return JsonResponse(
                {"success": False, "message": error_message},
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


@login_required
@permissions_required(["assets.basic_access"])
@require_POST
def mark_request_canceled(request, request_id: int):
    """Render view to mark a order request as canceled."""
    # Check Cooldown
    cooldown = get_apr_cooldown(request, request_id, "canceled")
    if cooldown:
        msg = _("You are on cooldown. Please wait 60 seconds before trying again.")
        return JsonResponse(
            {"success": True, "message": msg},
            status=HTTPStatus.FORBIDDEN,
            safe=False,
        )

    user_request = get_object_or_404(Request, pk=request_id)
    is_completed = user_request.mark_request(
        user=request.user,
        status=Request.STATUS_CANCELLED,
        closed=True,
        can_requestor_edit=True,
    )

    if is_completed:
        # Set Cooldown
        set_apr_cooldown(request.user, request_id, "canceled")
        msg = _(
            "The request for Order {user_request_pk} from {user_request_requesting_user} has been closed as cancelled."
        ).format(
            user_request_pk=user_request.pk,
            user_request_requesting_user=user_request.requesting_user,
        )

        user_request.notify_request_canceled(user=request.user)

        return JsonResponse(
            {"success": True, "message": msg},
            status=HTTPStatus.OK,
            safe=False,
        )
    msg = _(
        "The request for Order {user_request_pk} from {user_request_requesting_user} has failed."
    ).format(
        user_request_pk=user_request.pk,
        user_request_requesting_user=user_request.requesting_user,
    )

    return JsonResponse(
        {"success": False, "message": msg},
        status=HTTPStatus.BAD_REQUEST,
        safe=False,
    )


@login_required
@permissions_required(["assets.manage_requests"])
@require_POST
def mark_request_completed(request, request_id: int):
    """Render view to mark a order request as completed."""
    # Check Cooldown
    cooldown = get_apr_cooldown(request, request_id, "completed")
    if cooldown:
        return JsonResponse(
            {
                "success": False,
                "message": _(
                    "You are on cooldown. Please wait 60 seconds before trying again."
                ),
            },
            status=HTTPStatus.FORBIDDEN,
            safe=False,
        )

    user_request = get_object_or_404(Request, pk=request_id)
    is_completed = user_request.mark_request(
        user=request.user,
        status=Request.STATUS_COMPLETED,
        closed=True,
        can_requestor_edit=False,
    )

    if is_completed:
        # Set Cooldown
        set_apr_cooldown(request.user, request_id, "completed")
        msg = _(
            "The request for Order {user_request_pk} from {user_request_requesting_user} has been closed as completed."
        ).format(
            user_request_pk=user_request.pk,
            user_request_requesting_user=user_request.requesting_user,
        )
        user_request.notify_request_completed()
        return JsonResponse(
            {"success": True, "message": msg},
            status=HTTPStatus.OK,
            safe=False,
        )
    msg = _(
        "The request for Order {user_request_pk} from {user_request_requesting_user} has failed."
    ).format(
        user_request_pk=user_request.pk,
        user_request_requesting_user=user_request.requesting_user,
    )

    return JsonResponse(
        {"success": False, "message": msg},
        status=HTTPStatus.BAD_REQUEST,
        safe=False,
    )


@login_required
@permissions_required(["assets.manage_requests"])
@require_POST
def mark_request_open(request, request_id: int):
    """Render view to mark a order request as open."""
    # Check Cooldown
    cooldown = get_apr_cooldown(request, request_id, "open")
    if cooldown:
        msg = _("You are on cooldown. Please wait 60 seconds before trying again.")
        return JsonResponse(
            {"success": True, "message": msg},
            status=HTTPStatus.FORBIDDEN,
            safe=False,
        )

    user_request = get_object_or_404(Request, pk=request_id)
    is_completed = user_request.mark_request(
        user=request.user,
        status=Request.STATUS_OPEN,
        closed=False,
    )

    if is_completed:
        # Set Cooldown
        set_apr_cooldown(request.user, request_id, "open")
        msg = _(
            "The request for Order {user_request_pk} from {user_request_requesting_user} has been reopened."
        ).format(
            user_request_pk=user_request.pk,
            user_request_requesting_user=user_request.requesting_user,
        )
        user_request.notify_request_open(request)
        return JsonResponse(
            {"success": True, "message": msg},
            status=HTTPStatus.OK,
            safe=False,
        )
    msg = _(
        "The request for Order {user_request_pk} from {user_request_requesting_user} has failed."
    ).format(
        user_request_pk=user_request.pk,
        user_request_requesting_user=user_request.requesting_user,
    )

    return JsonResponse(
        {"success": False, "message": msg},
        status=HTTPStatus.BAD_REQUEST,
        safe=False,
    )
