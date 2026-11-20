"""Request models: orders of assets and their items."""

# Django
from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.authentication.models import Permission, User

# Alliance Auth (External Libs)
from eve_sde.models.types import ItemType

# AA Assets
from assets.helpers.discord import send_user_notification
from assets.managers.general import GeneralManager
from assets.managers.request import RequestManager
from assets.models.assets import Assets
from assets.providers import logger


def users_with_permission(
    permission: Permission, include_superusers=True
) -> models.QuerySet:
    """returns queryset of users that have the given Django permission

    Args:
        permission: required permission
        include_superusers: whether superusers are included in the returned list

    Taken from the `allianceauth-app-utils` package.
    Credits to: Erik Kalkoken
    """
    user_model = permission.user_set.model

    users_qs = (
        permission.user_set.all()
        | user_model.objects.filter(
            groups__in=list(permission.group_set.values_list("pk", flat=True))
        )
        | user_model.objects.select_related("profile").filter(
            profile__state__in=list(permission.state_set.values_list("pk", flat=True))
        )
    )
    if include_superusers:
        users_qs |= user_model.objects.filter(is_superuser=True)
    return users_qs.distinct()


class Request(models.Model):
    """A request system for Orders."""

    objects = RequestManager()

    name = models.CharField(
        max_length=100,
        help_text="Name of the Requestor",
        blank=True,
        null=True,
    )

    requesting_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="The requesting user",
    )
    approver_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="+",
        help_text="The user that manage the request",
    )

    STATUS_OPEN = "OP"
    STATUS_COMPLETED = "CD"
    STATUS_CANCELLED = "CL"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    status = models.CharField(
        help_text="Status of the Order request",
        choices=STATUS_CHOICES,
        max_length=2,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    closed_at = models.DateTimeField(blank=True, null=True, db_index=True)

    class Meta:
        default_permissions = ()

    def __str__(self) -> str:
        character_name = self.requesting_character_name()
        return f"{character_name}'s request"

    def __repr__(self) -> str:
        character_name = self.requesting_character_name()
        return (
            f"{self.__class__.__name__}(id={self.pk}, "
            f"requesting_user='{character_name}', "
        )

    def convert_order_to_notifiy(self) -> str:
        """Convert order to a string for notification."""
        requests = RequestAssets.objects.filter(request=self)
        msg = ""
        for request in requests:
            msg += f"\n{request.eve_type.name} x {request.quantity}"
        return msg

    def requesting_character_name(self) -> str:
        """Return main character's name of the requesting user safely."""
        try:
            return self.requesting_user.profile.main_character.character_name
        except AttributeError:
            return "?"

    def mark_request(
        self, user: User, status: str, closed: bool, can_requestor_edit: bool = False
    ) -> bool:
        """Change the status of a order request."""
        admin = GeneralManager.has_manage_requests_access(user)

        if admin or (can_requestor_edit and self.requesting_user == user):
            logger.debug("Success to mark request")
            if closed:
                self.closed_at = timezone.now()
            else:
                self.closed_at = None

            if status in {Request.STATUS_COMPLETED}:
                approver_user = user
            else:
                approver_user = None

            self.approver_user = approver_user
            self.status = status
            self.save()
            return True

        logger.debug("Failed to mark")
        return False

    def notify_new_request(self) -> None:
        """Notify approvers that a Order request has been created."""
        users = list(self.approvers())

        title = _("{requesting_user} has Requested a Order").format(
            requesting_user=self.requesting_user
        )
        msg = _("{requesting_user} has requested the following items:{items}\n").format(
            requesting_user=self.requesting_user,
            items=self.convert_order_to_notifiy(),
        )

        for approver in users:
            send_user_notification.delay(
                user_id=approver.pk,
                title=title,
                message=mark_safe(msg),
                embed_message=True,
                level="info",
            )

    def notify_request_completed(self) -> None:
        """Notify requestor that a Order marked as completed."""
        title = _(
            "{approver} has completed the Order for {requestor} ID: {request_id}."
        ).format(
            approver=self.approver_user,
            requestor=self.requesting_user,
            request_id=self.pk,
        )
        msg = _("{approver} has completed the following items:{items}\n").format(
            approver=self.approver_user,
            items=self.convert_order_to_notifiy(),
        )

        send_user_notification.delay(
            user_id=self.requesting_user.pk,
            title=title,
            message=mark_safe(msg),
            embed_message=True,
            level="success",
        )

    def notify_request_canceled(self, user=None) -> None:
        """Notify approvers and requestor that a Order marked as canceled."""
        users = list(self.approvers())

        if self.requesting_user == user:
            canceler = self.requesting_user
        else:
            canceler = user
            users += [self.requesting_user]

        title = _(
            "{canceler} has canceled the Order for {requestor} ID: {request_id}."
        ).format(
            canceler=canceler,
            requestor=self.requesting_user,
            request_id=self.pk,
        )
        msg = _("{canceler} has canceled the following items:{items}\n").format(
            canceler=canceler,
            items=self.convert_order_to_notifiy(),
        )

        for approver in users:
            send_user_notification.delay(
                user_id=approver.pk,
                title=title,
                message=mark_safe(msg),
                embed_message=True,
                level="danger",
            )

    def notify_request_open(self, user: User) -> None:
        """Notify requestor that a Order marked as reopened."""
        title = _(
            "{user} has reopened the Order for {requestor} ID: {request_id}."
        ).format(
            user=user,
            requestor=self.requesting_user,
            request_id=self.pk,
        )
        msg = _("{user} has reopened the following items:{items}\n").format(
            user=user,
            items=self.convert_order_to_notifiy(),
        )

        send_user_notification.delay(
            user_id=self.requesting_user.pk,
            title=title,
            message=mark_safe(msg),
            embed_message=True,
            level="warning",
        )

    @classmethod
    def approvers(cls) -> models.QuerySet[User]:
        """Return queryset of all approvers."""
        permission = Permission.objects.select_related("content_type").get(
            content_type__app_label=cls._meta.app_label, codename="manage_requests"
        )
        return users_with_permission(permission)


class RequestAssets(models.Model):
    """A Request Assets Information Model."""

    name = models.CharField(
        max_length=100,
        help_text="Name of the Asset",
    )

    request = models.ForeignKey(
        Request,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="The request this asset belongs to",
    )

    asset_pk = models.PositiveBigIntegerField(
        help_text="The asset this request belongs to",
    )

    asset_location_id = models.PositiveBigIntegerField(
        help_text="The asset location this request belongs to",
    )

    asset_location_flag = models.CharField(
        help_text="The asset location flag this request belongs to",
        choices=Assets.LocationFlag.choices,
        max_length=36,
    )

    eve_type = models.ForeignKey(
        ItemType,
        on_delete=models.CASCADE,
        related_name="+",
        help_text="The asset type this request belongs to",
    )

    quantity = models.PositiveIntegerField(
        help_text="Quantity of assets",
        default=1,
    )

    class Meta:
        default_permissions = ()
