# Standard Library
from http import HTTPStatus

# Third Party
from ninja import NinjaAPI

# Django
from django.urls import reverse
from django.utils.translation import gettext as _

# AA Assets
from assets.api import schema
from assets.helpers.admin import queue_admin_tasks
from assets.helpers.eveonline import get_character_portrait_url
from assets.managers import GeneralManager
from assets.models import Request
from assets.models.general import UserSettings
from assets.providers import logger


class GeneralApiEndpoints:
    tags = ["General"]

    def __init__(self, api: NinjaAPI):
        @api.get(
            "menu/",
            response={
                HTTPStatus.OK: schema.MenuSchema,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Get Assets navigation menu",
        )
        def get_menu(request):
            left_menu: list[schema.MenuLink] = [
                schema.MenuLink(name=_("Locations"), link="/"),
            ]
            if GeneralManager.has_manage_requests_access(request.user):
                open_requests = Request.objects.open_requests_total_count()
                left_menu.append(
                    schema.MenuLink(
                        name=_("Requests"),
                        link="/requests/",
                        badge=open_requests or None,
                        has_errors=bool(open_requests),
                    )
                )
            else:
                left_menu.append(
                    schema.MenuLink(name=_("My Requests"), link="/requests/")
                )
            left_menu.append(schema.MenuLink(name=_("Settings"), link="/settings/"))

            right_menu: list[schema.MenuLink] = [
                schema.MenuLink(
                    name=_("Add Character"),
                    link=reverse("assets:add_char"),
                    is_external=True,
                )
            ]
            if GeneralManager.has_manage_corporation_access(request.user):
                right_menu.append(
                    schema.MenuLink(
                        name=_("Add Corporation"),
                        link=reverse("assets:add_corp"),
                        is_external=True,
                    )
                )
            if request.user.is_superuser:
                right_menu.append(
                    schema.MenuLink(name=_("Administration"), link="/admin/")
                )
            return schema.MenuSchema(left_links=left_menu, right_links=right_menu)

        @api.get(
            "user/",
            response={
                HTTPStatus.OK: schema.UserData,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Get the current user and their rights",
        )
        def get_user(request):
            main_character = request.user.profile.main_character
            if main_character is not None:
                character_id = main_character.character_id
                character_name = main_character.character_name
                corporation_id = main_character.corporation_id
                corporation_name = main_character.corporation_name
                alliance_id = main_character.alliance_id
                alliance_name = main_character.alliance_name
            else:
                character_id = 0
                character_name = ""
                corporation_id = 0
                corporation_name = ""
                alliance_id = None
                alliance_name = None

            portrait_url = (
                get_character_portrait_url(
                    character_id=character_id,
                    character_name=character_name,
                    as_html=False,
                )
                if character_id
                else None
            )

            return HTTPStatus.OK, schema.UserData(
                user_id=request.user.id,
                character_id=character_id,
                character_name=character_name,
                corporation_id=corporation_id,
                corporation_name=corporation_name,
                alliance_id=alliance_id,
                alliance_name=alliance_name,
                portrait=portrait_url,
                is_admin=request.user.is_superuser,
                can_manage_requests=GeneralManager.has_manage_requests_access(
                    request.user
                ),
                can_add_corporation=GeneralManager.has_manage_corporation_access(
                    request.user
                ),
            )

        @api.post(
            "admin/tasks/",
            response={
                HTTPStatus.OK: schema.ActionResponse,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Queue administration tasks (superusers only)",
        )
        def queue_tasks(request, payload: schema.AdminTasksRequest):
            if not request.user.is_superuser:
                return HTTPStatus.FORBIDDEN, {"error": _("Permission Denied")}

            queued = queue_admin_tasks(
                force_refresh=payload.force_refresh,
                clear_etags=payload.clear_etags,
                update_assets=payload.update_assets,
                update_locations=payload.update_locations,
                update_parent_locations=payload.update_parent_locations,
            )
            logger.info("User %s queued admin tasks: %s", request.user, queued)
            return HTTPStatus.OK, schema.ActionResponse(
                success=bool(queued),
                message=" ".join(queued) if queued else _("No task selected."),
            )

        @api.get(
            "settings/",
            response={
                HTTPStatus.OK: schema.UserSettingsSchema,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Get current user's settings",
        )
        def get_user_settings(request):
            settings = UserSettings.objects.get_or_create(user=request.user)[0]
            return schema.UserSettingsSchema(
                disable_notifications=settings.disable_notifications
            )

        @api.put(
            "settings/",
            response={
                HTTPStatus.OK: schema.UserSettingsSchema,
                HTTPStatus.FORBIDDEN: schema.ErrorSchema,
            },
            tags=self.tags,
            summary="Update current user's settings",
        )
        def update_user_settings(request, payload: schema.UserSettingsUpdateRequest):
            settings = UserSettings.objects.get_or_create(user=request.user)[0]
            settings.disable_notifications = payload.disable_notifications
            settings.save(update_fields=["disable_notifications"])
            return schema.UserSettingsSchema(
                disable_notifications=settings.disable_notifications
            )
