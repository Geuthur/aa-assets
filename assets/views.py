"""PvE Views"""

import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.cache import cache

# Django
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST
from esi.decorators import token_required

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCorporationInfo

from assets.hooks import add_info_to_context, get_extension_logger
from assets.models import Owner, Request
from assets.tasks import update_assets_for_owner

logger = get_extension_logger(__name__)


def build_apr_cooldown_cache_tag(user, request_id, mode):
    return f"cooldown_request_{user}_{request_id}_{mode}"


def get_apr_cooldown(request, request_id, mode):
    if cache.get(build_apr_cooldown_cache_tag(request.user, request_id, mode), False):
        msg = _("You are on cooldown. Please wait 60 seconds before trying again.")
        messages.error(
            request,
            msg,
        )
        return True
    return False


def set_apr_cooldown(user, request_id, mode):
    """Set a 60 sec cooldown forthe Approver"""
    return cache.set(build_apr_cooldown_cache_tag(user, request_id, mode), True, (60))


@login_required
@permission_required("assets.basic_access")
def index(request):
    context = {}
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
    quantities = request.POST.getlist("quantity[]")
    item_names = request.POST.getlist("item_name[]")
    item_ids = request.POST.getlist("item_id[]")

    items = []
    msg = ""
    for item_id, name, quantity in zip(item_ids, item_names, quantities):
        if quantity:
            msg += f"{name} - {quantity} Stück\n"
            item_info = {"item_id": item_id, "name": name, "quantity": quantity}
            items.append(item_info)

    # Convert the items list to a JSON string
    items_json = json.dumps(items)

    user = request.user
    user_request = Request.objects.create(
        order=items_json,
        requesting_user=user,
        status=Request.STATUS_OPEN,
    )

    user_request.notify_new_request()
    messages.success(
        request,
        format_html("Your Order has been Requested."),
    )

    return redirect("assets:index")


@login_required
@permission_required("assets.basic_access")
@require_POST
def mark_request_canceled(request, request_id: int):
    """Render view to mark a order request as canceled."""
    # Check Cooldown
    cooldown = get_apr_cooldown(request, request_id, "canceled")
    if cooldown:
        return redirect("assets:index")

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

        messages.info(
            request,
            msg,
        )
        return redirect("assets:index")
    msg = _(
        "The request for Order {user_request_pk} from {user_request_requesting_user} has failed."
    ).format(
        user_request_pk=user_request.pk,
        user_request_requesting_user=user_request.requesting_user,
    )

    messages.error(
        request,
        msg,
    )
    return redirect("assets:index")


@login_required
@permission_required("assets.manage_requests")
@require_POST
def mark_request_completed(request, request_id: int):
    """Render view to mark a order request as completed."""
    # Check Cooldown
    cooldown = get_apr_cooldown(request, request_id, "completed")
    if cooldown:
        return redirect("assets:index")

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
        messages.info(
            request,
            msg,
        )
        return redirect("assets:index")
    msg = _(
        "The request for Order {user_request_pk} from {user_request_requesting_user} has failed."
    ).format(
        user_request_pk=user_request.pk,
        user_request_requesting_user=user_request.requesting_user,
    )

    messages.error(
        request,
        msg,
    )
    return redirect("assets:index")


@login_required
@permission_required("assets.manage_requests")
@require_POST
def mark_request_open(request, request_id: int):
    """Render view to mark a order request as open."""
    # Check Cooldown
    cooldown = get_apr_cooldown(request, request_id, "open")
    if cooldown:
        return redirect("assets:index")

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
        messages.info(
            request,
            msg,
        )
        return redirect("assets:index")
    msg = _(
        "The request for Order {user_request_pk} from {user_request_requesting_user} has failed."
    ).format(
        user_request_pk=user_request.pk,
        user_request_requesting_user=user_request.requesting_user,
    )

    messages.error(
        request,
        msg,
    )
    return redirect("assets:index")
