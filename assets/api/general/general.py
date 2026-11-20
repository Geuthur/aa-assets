# Standard Library
from http import HTTPStatus

# Third Party
from ninja import NinjaAPI

# AA Assets
from assets.api import schema
from assets.models.general import UserSettings


class GeneralApiEndpoints:
    tags = ["General"]

    def __init__(self, api: NinjaAPI):
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
