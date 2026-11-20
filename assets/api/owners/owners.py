"""Owner endpoints: the update status of every owner."""

# Standard Library
from http import HTTPStatus

# Third Party
from ninja import NinjaAPI

# Django
from django.core.handlers.wsgi import WSGIRequest
from django.utils.translation import gettext as _

# AA Assets
from assets.api import schema
from assets.models import Owner


def _serialize_owner(owner: Owner) -> schema.OwnerSchema:
    """Serialize one owner with its aggregate update status."""
    status = owner.get_status
    last_update = (
        owner.assets_update_status.exclude(last_update_finished_at__isnull=True)
        .order_by("-last_update_finished_at")
        .values_list("last_update_finished_at", flat=True)
        .first()
    )
    character = owner.character.character if owner.character else None
    return schema.OwnerSchema(
        id=owner.pk,
        name=owner.name,
        owner_type="corporation" if owner.corporation else "character",
        character_id=character.character_id if character else None,
        corporation_id=(
            owner.corporation.corporation_id if owner.corporation else None
        ),
        active=owner.is_active,
        update_status=status.value,
        update_status_label=str(status.label),
        last_update=last_update,
    )


def _serialize_owner_detail(owner: Owner) -> schema.OwnerDetailSchema:
    """Serialize one owner with the status of every section."""
    summary = _serialize_owner(owner)
    sections = [
        schema.OwnerUpdateStatusSchema(
            section=status.section,
            section_label=str(Owner.update_section_class(status.section).label),
            is_success=status.is_success,
            has_token_error=status.has_token_error,
            error_message=status.error_message,
            last_run_finished_at=status.last_run_finished_at,
            last_update_finished_at=status.last_update_finished_at,
        )
        for status in owner.assets_update_status.order_by("section")
    ]
    return schema.OwnerDetailSchema(**summary.dict(), sections=sections)


class OwnersApiEndpoints:
    tags = ["Owners"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "owners/",
            response={
                HTTPStatus.OK: list[schema.OwnerSchema],
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="List the owners visible to the user with their update status",
        )
        def list_owners(request: WSGIRequest):
            owners = Owner.objects.visible_to(request.user).select_related(
                "character__character", "corporation"
            )
            output = [_serialize_owner(owner) for owner in owners]
            return HTTPStatus.OK, sorted(output, key=lambda o: o.name.lower())

        @api.get(
            "owners/{owner_id}/",
            response={
                HTTPStatus.OK: schema.OwnerDetailSchema,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
                HTTPStatus.NOT_FOUND: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Get an owner with the update status of its sections",
        )
        def get_owner(request: WSGIRequest, owner_id: int):
            owner = (
                Owner.objects.select_related("character__character", "corporation")
                .filter(pk=owner_id)
                .first()
            )
            if owner is None:
                return HTTPStatus.NOT_FOUND, {"error": _("Owner not found")}

            if not Owner.objects.visible_to(request.user).filter(pk=owner.pk).exists():
                return HTTPStatus.FORBIDDEN, {"error": _("Permission Denied")}

            return HTTPStatus.OK, _serialize_owner_detail(owner)
