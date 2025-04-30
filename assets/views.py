"""PvE Views"""

import datetime
from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.cache import cache

# Django
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from esi.decorators import token_required

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


@login_required
@permission_required("assets.basic_access")
def index(request):
    context = {
        "corporation_id": request.user.profile.main_character.corporation_id,
        "title": _("Assets"),
        "forms": {
            "single_request": forms.RequestOrder(),
            "multi_request": forms.RequestMultiOrder(
                location_flag="corpsag5", location_id=1042478386825
            ),
        },
    }
    context = add_info_to_context(request, context)

    return render(request, "assets/index.html", context=context)


@login_required
@token_required(
    scopes=["esi-universe.read_structures.v1", "esi-assets.read_corporation_assets.v1"]
)
@permission_required("assets.basic_access")
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
    skip_date = timezone.now() - datetime.timedelta(hours=2)

    if owner.last_update <= skip_date:
        update_assets_for_owner.apply_async(
            args=[owner.pk], kwargs={"force_refresh": True}, priority=6
        )
        msg = f"{owner.name} successfully added/updated to Assets"
        messages.info(request, msg)
        return redirect("assets:index")
    msg = f"{owner.name} is already up to date"
    messages.warning(request, msg)
    return redirect("assets:index")


@login_required
@token_required(scopes=["esi-universe.read_structures.v1", "esi-assets.read_assets.v1"])
@permission_required("assets.basic_access")
def add_char(request, token) -> HttpResponse:
    char = get_object_or_404(
        CharacterOwnership, character__character_id=token.character_id
    )
    owner, _ = Owner.objects.update_or_create(
        corporation=None,
        character=char,
    )
    skip_date = timezone.now() - datetime.timedelta(hours=2)

    if owner.last_update <= skip_date:
        update_assets_for_owner.apply_async(
            args=[owner.pk], kwargs={"force_refresh": True}, priority=6
        )
        msg = f"{owner.name} successfully added/updated to Assets"
        messages.info(request, msg)
        return redirect("assets:index")
    msg = f"{owner.name} is already up to date"
    messages.warning(request, msg)
    return redirect("assets:index")


@login_required
@permission_required("assets.basic_access")
@require_POST
def create_order(request):
    """Render view to create a new order request."""
    # Check Permission
    form = forms.RequestOrder(request.POST)
    form_multi = forms.RequestMultiOrder(request.POST)

    logger.info(form_multi)

    logger.info(request.POST)

    if form.is_valid():
        logger.info(form.cleaned_data)
        amount = int(form.cleaned_data["amount"])
        asset_pk = request.POST.get("asset_pk")
        user = request.user

        try:
            asset = Assets.objects.get(pk=asset_pk)
        except Assets.DoesNotExist:
            msg = "The asset does not exist."
            return JsonResponse(
                {"success": True, "message": msg},
                status=HTTPStatus.NOT_FOUND,
                safe=False,
            )

        requests = RequestAssets.objects.filter(
            asset=asset,
            requestor__status=Request.STATUS_OPEN,
        ).values_list("quantity", flat=True)

        if requests and sum(requests) + amount > asset.quantity:
            msg = "The requested amount exceeds the available quantity."
            return JsonResponse(
                {"success": True, "message": msg},
                status=HTTPStatus.FORBIDDEN,
                safe=False,
            )

        user_request = Request.objects.create(
            requesting_user=user,
            status=Request.STATUS_OPEN,
        )

        RequestAssets.objects.create(
            name=user_request.requesting_user.username,
            requestor=user_request,
            asset=asset,
            quantity=amount,
        )

        user_request.notify_new_request()
        msg = f"The request for Order {user_request.requesting_user.username} has been created."
        return JsonResponse(
            {"success": True, "message": msg},
            status=HTTPStatus.OK,
            safe=False,
        )
    if form_multi.is_valid():
        logger.info(form_multi.cleaned_data.get("items", None))
        return JsonResponse(
            {"success": True, "message": "Order created successfully."},
            status=HTTPStatus.OK,
            safe=False,
        )

    msg = "Invalid Form"
    return JsonResponse(
        {"success": True, "message": msg},
        status=HTTPStatus.NOT_FOUND,
        safe=False,
    )


@login_required
@permission_required("assets.basic_access")
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
@permission_required("assets.manage_requests")
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
@permission_required("assets.manage_requests")
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
