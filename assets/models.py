"""Models for assets."""

from django.contrib.auth.models import Permission, User

# Django
from django.db import models, transaction
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from esi.errors import TokenError
from esi.models import Token

# Alliance Auth (External Libs)
from eveuniverse.models import EveEntity, EveSolarSystem, EveType

# Alliance Auth
from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.evelinks import dotlan
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from app_utils.django import users_with_permission

from assets.helpers.discord import send_user_notification
from assets.hooks import get_extension_logger
from assets.managers import (
    AssetsManager,
    LocationManager,
    OwnerManager,
    RequestManager,
    get_market_price,
)
from assets.providers import esi
from assets.task_helpers.etag_helpers import (
    HTTPGatewayTimeoutError,
    NotModifiedError,
    etag_results,
)

logger = get_extension_logger(__name__)


def get_or_create_location(location_id: int) -> "Location":
    """Get or create a location sync - helper function."""
    obj, _ = Location.objects.get_or_create_esi(location_id=location_id)
    return obj


class General(models.Model):
    """General model for app permissions"""

    class Meta:
        managed = False
        permissions = (
            ("basic_access", "Can access this app"),
            ("corporation_access", "Can access own corporation assets"),
            ("admin_access", "Can access all assets."),
            ("manage_corporation", "Can add corporation assets"),
            ("manage_requests", "Can manage requests"),
        )
        default_permissions = ()


class Owner(models.Model):
    """A model defining an owner of assets."""

    corporation = models.OneToOneField(
        EveCorporationInfo,
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="Corporation used for syncing",
        related_name="+",
    )
    character = models.ForeignKey(
        CharacterOwnership,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        help_text="character used for syncing",
        related_name="+",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=("whether this owner is currently included in the sync process"),
    )
    last_update = models.DateTimeField(auto_now=True)

    objects = OwnerManager()

    class Meta:
        default_permissions = ()

    @property
    def name(self) -> str:
        """Return the name of this owner."""
        try:
            if self.corporation:
                return self.corporation.corporation_name
            return self.eve_character_strict.character_name
        except (ValueError, AttributeError):
            return ""

    @property
    def corporation_strict(self) -> EveCorporationInfo:
        """Return corporation of this owner when it exists, or raises error."""
        if not self.corporation:
            raise ValueError("No corporation defined")
        return self.corporation

    @property
    def eve_character_strict(self) -> EveCharacter:
        """Return character of this owner when it exists, or raises error."""
        if not self.character or not self.character.character:
            raise ValueError("No character defined")
        return self.character.character

    def update_assets_esi(self, force_refresh=False):
        try:
            if self.corporation:
                token = self.valid_token(
                    [
                        "esi-universe.read_structures.v1",
                        "esi-assets.read_corporation_assets.v1",
                    ]
                )
                assets = self._fetch_corporate_assets(
                    token, force_refresh=force_refresh
                )
            else:
                token = self.valid_token(
                    ["esi-universe.read_structures.v1", "esi-assets.read_assets.v1"]
                )
                assets = self._fetch_personal_assets(token, force_refresh=force_refresh)
        except NotModifiedError:
            logger.info("No new Assets for: %s", self.name)
            return
        except HTTPGatewayTimeoutError:
            logger.info("Gateway Timeout for: %s", self.name)
            return

        items = []
        item_ids = list(
            {
                asset["type_id"]
                for asset in assets
                if get_market_price(asset["type_id"]) is None
            }
        )

        if item_ids:
            # Update or create prices for all items and save them in cache
            Assets.objects.update_or_create_prices(item_ids)

        for asset in assets:
            try:
                price = float(get_market_price(asset.get("type_id")))
            except AttributeError:
                price = None

            location_flag = Assets.LocationFlag.from_esi_data(asset["location_flag"])
            eve_type, _ = EveType.objects.get_or_create_esi(id=asset["type_id"])
            asset_item = Assets(
                location=get_or_create_location(asset["location_id"]),
                location_flag=location_flag,
                location_type=asset.get("location_type"),
                eve_type=eve_type,
                item_id=asset.get("type_id"),
                quantity=asset.get("quantity"),
                singleton=asset.get("is_singleton"),
                blueprint_copy=asset.get("is_blueprint_copy"),
                owner=self,
                price=price,
            )
            items.append(asset_item)

        try:
            if items:
                with transaction.atomic():
                    # Delete all assets before adding new ones
                    self.flush_assets()
                    # Create Bulk
                    Assets.objects.bulk_create(items)
                    logger.info("Updated %s assets for %s", len(assets), self.name)

            else:
                logger.info("No updates found for %s", self.name)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "Error while updating assets for %s: %s",
                self.name,
                e,
            )

        self.last_update = timezone.now()
        self.save()
        self.update_order_assets()

    def update_order_assets(self):
        # Filter offene Bestellungen
        orders = RequestAssets.objects.filter(request__status=Request.STATUS_OPEN)

        orders_to_update = []
        for order in orders:
            try:
                asset = Assets.objects.get(
                    eve_type=order.eve_type,
                    location_id=order.asset_location_id,
                    location_flag=order.asset_location_flag,
                )
            except Assets.DoesNotExist:
                continue
            if asset:
                order.asset_pk = asset.pk
                orders_to_update.append(order)

        # Bulk-Update der Bestellungen
        if orders_to_update:
            logger.info("Updated %s orders for %s", len(orders_to_update), self.name)
            RequestAssets.objects.bulk_update(orders_to_update, ["asset_pk"])

    def _fetch_corporate_assets(self, token, force_refresh=False) -> list:
        """Fetch all assets for this owner from ESI."""
        asset_esi = esi.client.Assets.get_corporations_corporation_id_assets(
            corporation_id=self.corporation_strict.corporation_id,
            token=token.valid_access_token(),
        )
        assets = etag_results(asset_esi, token, force_refresh=force_refresh)
        return assets

    def _fetch_personal_assets(self, token, force_refresh=False) -> list:
        """Fetch all assets for this owner from ESI."""
        asset_esi = esi.client.Assets.get_characters_character_id_assets(
            character_id=self.eve_character_strict.character_id,
            token=token.valid_access_token(),
        )
        assets = etag_results(asset_esi, token, force_refresh=force_refresh)
        return assets

    def valid_token(self, scopes) -> Token:
        """Return a valid token for the owner or raise exception."""

        token = (
            Token.objects.filter(
                user=self.character.user,
                character_id=self.eve_character_strict.character_id,
            )
            .require_scopes(scopes)
            .require_valid()
            .first()
        )
        if not token:
            raise TokenError(f"{self}: No valid token found")

        return token

    def flush_assets(self):
        """Delete all assets for this owner."""
        delete_query = Assets.objects.filter(owner=self)  # Flush Assets
        if delete_query.exists():
            delete_query._raw_delete(delete_query.db)


class Location(models.Model):
    """An Eve Online location: Station or Upwell Structure or Solar System"""

    _SOLAR_SYSTEM_ID_START = 30_000_000
    _SOLAR_SYSTEM_ID_END = 33_000_000
    _STATION_ID_START = 60_000_000
    _STATION_ID_END = 64_000_000

    id = models.PositiveBigIntegerField(
        primary_key=True,
        help_text=(
            "Eve Online location ID, "
            "either item ID for stations or structure ID for structures"
        ),
    )
    parent = models.ForeignKey(
        "Location",
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        help_text=("Eve Online location ID of the parent object"),
        related_name="+",
    )

    name = models.CharField(
        max_length=100,
        help_text="In-game name of this station or structure",
    )
    eve_solar_system = models.ForeignKey(
        EveSolarSystem,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        related_name="+",
    )
    eve_type = models.ForeignKey(
        EveType,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        related_name="+",
    )
    owner = models.ForeignKey(
        EveEntity,
        on_delete=models.SET_DEFAULT,
        default=None,
        null=True,
        blank=True,
        help_text="corporation this station or structure belongs to",
        related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    objects = LocationManager()

    class Meta:
        default_permissions = ()

    def __str__(self) -> str:
        if self.name:
            return self.name
        if self.eve_type:
            return str(self.eve_type)
        return f"Location #{self.id}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, name='{self.name}')"

    @property
    def is_empty(self) -> bool:
        """Return True if this is an empty location, else False."""
        return not self.eve_solar_system and not self.eve_type and not self.parent_id

    @property
    def solar_system_url(self) -> str:
        """Return dotlan URL for this solar system."""
        try:
            return dotlan.solar_system_url(self.eve_solar_system.name)
        except AttributeError:
            return ""

    @property
    def is_solar_system(self) -> bool:
        """Return True if this location is a solar system, else False."""
        return self.is_solar_system_id(self.id)

    @property
    def is_station(self) -> bool:
        """Return True if this location is a station, else False."""
        return self.is_station_id(self.id)

    @classmethod
    def is_solar_system_id(cls, location_id: int) -> bool:
        """Return True if the given ID is a solar system ID, else False."""
        return cls._SOLAR_SYSTEM_ID_START <= location_id <= cls._SOLAR_SYSTEM_ID_END

    @classmethod
    def is_station_id(cls, location_id: int) -> bool:
        """Return True if the given ID is a station ID, else False."""
        return cls._STATION_ID_START <= location_id <= cls._STATION_ID_END

    def full_qualified_name(self) -> str:
        """Return the full qualified name of this location."""
        if self.parent:
            return f"{self.parent.full_qualified_name()} - {str(self)}"
        return str(self)


class Assets(models.Model):
    """A Asset in Eve Online."""

    class LocationFlag(models.TextChoices):
        """A flag denoting the location of a assets."""

        ASSET_SAFETY = "AssetSafety", _("Asset Safety")
        AUTO_FIT = "AutoFit", _("Auto Fit")
        BONUS = "Bonus", _("Bonus")
        BOOSTER = "Booster", _("Booster")
        BOOSTER_BAY = "BoosterBay", _("Booster Hold")
        CAPSULE = "Capsule", _("Capsule")
        CARGO = "Cargo", _("Cargo")
        CORP_DELIVERIES = "CorpDeliveries", _("Corp Deliveries")
        CORP_S_A_G_1 = "CorpSAG1", _("Corp Security Access Group 1")
        CORP_S_A_G_2 = "CorpSAG2", _("Corp Security Access Group 2")
        CORP_S_A_G_3 = "CorpSAG3", _("Corp Security Access Group 3")
        CORP_S_A_G_4 = "CorpSAG4", _("Corp Security Access Group 4")
        CORP_S_A_G_5 = "CorpSAG5", _("Corp Security Access Group 5")
        CORP_S_A_G_6 = "CorpSAG6", _("Corp Security Access Group 6")
        CORP_S_A_G_7 = "CorpSAG7", _("Corp Security Access Group 7")
        CRATE_LOOT = "CrateLoot", _("Crate Loot")
        DELIVERIES = "Deliveries", _("Deliveries")
        DRONE_BAY = "DroneBay", _("Drone Bay")
        DUST_BATTLE = "DustBattle", _("Dust Battle")
        DUST_DATABANK = "DustDatabank", _("Dust Databank")
        FIGHTER_BAY = "FighterBay", _("Fighter Bay")
        FIGHTER_TUBE_0 = "FighterTube0", _("Fighter Tube 0")
        FIGHTER_TUBE_1 = "FighterTube1", _("Fighter Tube 1")
        FIGHTER_TUBE_2 = "FighterTube2", _("Fighter Tube 2")
        FIGHTER_TUBE_3 = "FighterTube3", _("Fighter Tube 3")
        FIGHTER_TUBE_4 = "FighterTube4", _("Fighter Tube 4")
        FLEET_HANGAR = "FleetHangar", _("Fleet Hangar")
        FRIGATE_ESCAPE_BAY = "FrigateEscapeBay", _("Frigate escape bay Hangar")
        HANGAR = "Hangar", _("Hangar")
        HANGAR_ALL = "HangarAll", _("Hangar All")
        HI_SLOT_0 = "HiSlot0", _("High power slot 1")
        HI_SLOT_1 = "HiSlot1", _("High power slot 2")
        HI_SLOT_2 = "HiSlot2", _("High power slot 3")
        HI_SLOT_3 = "HiSlot3", _("High power slot 4")
        HI_SLOT_4 = "HiSlot4", _("High power slot 5")
        HI_SLOT_5 = "HiSlot5", _("High power slot 6")
        HI_SLOT_6 = "HiSlot6", _("High power slot 7")
        HI_SLOT_7 = "HiSlot7", _("High power slot 8")
        HIDDEN_MODIFIERS = "HiddenModifiers", _("Hidden Modifiers")
        IMPLANT = "Implant", _("Implant")
        IMPOUNDED = "Impounded", _("Impounded")
        JUNKYARD_REPROCESSED = "JunkyardReprocessed", _(
            "This item was put into a junkyard through reprocessing."
        )
        JUNKYARD_TRASHED = "JunkyardTrashed", _(
            "This item was put into a junkyard through being trashed by its owner."
        )
        LO_SLOT_0 = "LoSlot0", _("Low power slot 1")
        LO_SLOT_1 = "LoSlot1", _("Low power slot 2")
        LO_SLOT_2 = "LoSlot2", _("Low power slot 3")
        LO_SLOT_3 = "LoSlot3", _("Low power slot 4")
        LO_SLOT_4 = "LoSlot4", _("Low power slot 5")
        LO_SLOT_5 = "LoSlot5", _("Low power slot 6")
        LO_SLOT_6 = "LoSlot6", _("Low power slot 7")
        LO_SLOT_7 = "LoSlot7", _("Low power slot 8")
        LOCKED = "Locked", _("Locked item, can not be moved unless unlocked")
        MED_SLOT_0 = "MedSlot0", _("Medium power slot 1")
        MED_SLOT_1 = "MedSlot1", _("Medium power slot 2")
        MED_SLOT_2 = "MedSlot2", _("Medium power slot 3")
        MED_SLOT_3 = "MedSlot3", _("Medium power slot 4")
        MED_SLOT_4 = "MedSlot4", _("Medium power slot 5")
        MED_SLOT_5 = "MedSlot5", _("Medium power slot 6")
        MED_SLOT_6 = "MedSlot6", _("Medium power slot 7")
        MED_SLOT_7 = "MedSlot7", _("Medium power slot 8")
        OFFICE_FOLDER = "OfficeFolder", _("Office Folder")
        PILOT = "Pilot", _("Pilot")
        PLANET_SURFACE = "PlanetSurface", _("Planet Surface")
        QUAFE_BAY = "QuafeBay", _("Quafe Bay")
        QUANTUM_CORE_ROOM = "QuantumCoreRoom", _("Quantum Core Room")
        REWARD = "Reward", _("Reward")
        RIG_SLOT_0 = "RigSlot0", _("Rig power slot 1")
        RIG_SLOT_1 = "RigSlot1", _("Rig power slot 2")
        RIG_SLOT_2 = "RigSlot2", _("Rig power slot 3")
        RIG_SLOT_3 = "RigSlot3", _("Rig power slot 4")
        RIG_SLOT_4 = "RigSlot4", _("Rig power slot 5")
        RIG_SLOT_5 = "RigSlot5", _("Rig power slot 6")
        RIG_SLOT_6 = "RigSlot6", _("Rig power slot 7")
        RIG_SLOT_7 = "RigSlot7", _("Rig power slot 8")
        SECONDARY_STORAGE = "SecondaryStorage", _("Secondary Storage")
        SERVICE_SLOT_0 = "ServiceSlot0", _("Service Slot 0")
        SERVICE_SLOT_1 = "ServiceSlot1", _("Service Slot 1")
        SERVICE_SLOT_2 = "ServiceSlot2", _("Service Slot 2")
        SERVICE_SLOT_3 = "ServiceSlot3", _("Service Slot 3")
        SERVICE_SLOT_4 = "ServiceSlot4", _("Service Slot 4")
        SERVICE_SLOT_5 = "ServiceSlot5", _("Service Slot 5")
        SERVICE_SLOT_6 = "ServiceSlot6", _("Service Slot 6")
        SERVICE_SLOT_7 = "ServiceSlot7", _("Service Slot 7")
        SHIP_HANGAR = "ShipHangar", _("Ship Hangar")
        SHIP_OFFLINE = "ShipOffline", _("Ship Offline")
        SKILL = "Skill", _("Skill")
        SKILL_IN_TRAINING = "SkillInTraining", _("Skill In Training")
        SPECIALIZED_AMMO_HOLD = "SpecializedAmmoHold", _("Specialized Ammo Hold")
        SPECIALIZED_COMMAND_CENTER_HOLD = "SpecializedCommandCenterHold", _(
            "Specialized Command Center Hold"
        )
        SPECIALIZED_FUEL_BAY = "SpecializedFuelBay", _("Specialized Fuel Bay")
        SPECIALIZED_GAS_HOLD = "SpecializedGasHold", _("Specialized Gas Hold")
        SPECIALIZED_INDUSTRIAL_SHIP_HOLD = "SpecializedIndustrialShipHold", _(
            "Specialized Industrial Ship Hold"
        )
        SPECIALIZED_LARGE_SHIP_HOLD = "SpecializedLargeShipHold", _(
            "Specialized Large Ship Hold"
        )
        SPECIALIZED_MATERIAL_BAY = "SpecializedMaterialBay", _(
            "Specialized Material Bay"
        )
        SPECIALIZED_MEDIUM_SHIP_HOLD = "SpecializedMediumShipHold", _(
            "Specialized Medium Ship Hold"
        )
        SPECIALIZED_MINERAL_HOLD = "SpecializedMineralHold", _(
            "Specialized Mineral Hold"
        )
        SPECIALIZED_ORE_HOLD = "SpecializedOreHold", _("Specialized Ore Hold")
        SPECIALIZED_PLANETARY_COMMODITIES_HOLD = (
            "SpecializedPlanetaryCommoditiesHold",
            _("Specialized Planetary Commodities Hold"),
        )
        SPECIALIZED_SALVAGE_HOLD = "SpecializedSalvageHold", _(
            "Specialized Salvage Hold"
        )
        SPECIALIZED_SHIP_HOLD = "SpecializedShipHold", _("Specialized Ship Hold")
        SPECIALIZED_SMALL_SHIP_HOLD = "SpecializedSmallShipHold", _(
            "Specialized Small Ship Hold"
        )
        STRUCTURE_ACTIVE = "StructureActive", _("Structure Active")
        STRUCTURE_FUEL = "StructureFuel", _("Structure Fuel")
        STRUCTURE_INACTIVE = "StructureInactive", _("Structure Inactive")
        STRUCTURE_OFFLINE = "StructureOffline", _("Structure Offline")
        SUB_SYSTEM_BAY = "SubSystemBay", _("Sub System Bay")
        SUB_SYSTEM_SLOT_0 = "SubSystemSlot0", _("Sub System Slot 0")
        SUB_SYSTEM_SLOT_1 = "SubSystemSlot1", _("Sub System Slot 1")
        SUB_SYSTEM_SLOT_2 = "SubSystemSlot2", _("Sub System Slot 2")
        SUB_SYSTEM_SLOT_3 = "SubSystemSlot3", _("Sub System Slot 3")
        SUB_SYSTEM_SLOT_4 = "SubSystemSlot4", _("Sub System Slot 4")
        SUB_SYSTEM_SLOT_5 = "SubSystemSlot5", _("Sub System Slot 5")
        SUB_SYSTEM_SLOT_6 = "SubSystemSlot6", _("Sub System Slot 6")
        SUB_SYSTEM_SLOT_7 = "SubSystemSlot7", _("Sub System Slot 7")
        UNLOCKED = "Unlocked", _("Unlocked item, can be moved")
        WALLET = "Wallet", _("Wallet")
        WARDROBE = "Wardrobe", _("Wardrobe")
        UNDEFINED = "Undefined", _("undefined")

        @classmethod
        def from_esi_data(cls, data: str) -> "Assets.LocationFlag":
            """Create new obj from ESI data."""
            try:
                return cls(data)
            except ValueError:
                return cls.UNDEFINED

    id = models.BigAutoField(primary_key=True)
    item_id = models.PositiveBigIntegerField(help_text="The EVE Item ID of the asset")
    owner = models.ForeignKey(
        Owner,
        on_delete=models.CASCADE,
        related_name="assets",
        help_text="Corporation that owns the asset",
    )
    eve_type = models.ForeignKey(
        EveType, on_delete=models.CASCADE, related_name="+", help_text="asset type"
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="assets",
        help_text="asset location",
    )
    location_flag = models.CharField(
        help_text="Additional location information",
        choices=LocationFlag.choices,
        max_length=36,
    )
    location_type = models.CharField(
        help_text="location type",
        max_length=100,
    )
    quantity = models.PositiveIntegerField(help_text="Number of assets", default=1)
    singleton = models.BooleanField(
        help_text="Singleton",
    )
    blueprint_copy = models.BooleanField(
        help_text="Blueprint Copy", null=True, default=None
    )
    price = models.FloatField(null=True, default=None)

    objects = AssetsManager()

    def __str__(self):
        return self.eve_type.name

    class Meta:
        default_permissions = ()
        indexes = [
            models.Index(fields=["location_id"]),
            models.Index(fields=["item_id"]),
        ]


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
        admin = user.has_perm("assets.manage_requests")

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

        title = _(f"{self.requesting_user} has Requested a Order")
        msg = _(
            f"{self.requesting_user} has requested the following items:{self.convert_order_to_notifiy()}\n"
        )

        for approver in users:
            send_user_notification.delay(
                user_id=approver.pk,
                title=title,
                message=format_html(msg),
                embed_message=True,
                level="info",
            )

    def notify_request_completed(self) -> None:
        """Notify requestor that a Order marked as completed."""
        title = _(
            f"{self.approver_user} has completed the Order for {self.requesting_user} ID: {self.pk}."
        )
        msg = _(
            f"{self.approver_user} has completed the following items:{self.convert_order_to_notifiy()}\n"
        )

        send_user_notification.delay(
            user_id=self.requesting_user.pk,
            title=title,
            message=format_html(msg),
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
            f"{canceler} has canceled the Order for {self.requesting_user} ID: {self.pk}."
        )
        msg = _(
            f"{canceler} has canceled the following items:{self.convert_order_to_notifiy()}\n"
        )

        for approver in users:
            send_user_notification.delay(
                user_id=approver.pk,
                title=title,
                message=format_html(msg),
                embed_message=True,
                level="danger",
            )

    def notify_request_open(self, request) -> None:
        """Notify requestor that a Order marked as reopened."""
        title = _(
            f"{request.user} has reopened the Order for {self.requesting_user} ID: {self.pk}."
        )
        msg = _(
            f"{request.user} has reopened the following items:{self.convert_order_to_notifiy()}\n"
        )

        send_user_notification.delay(
            user_id=self.requesting_user.pk,
            title=title,
            message=format_html(msg),
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
        EveType,
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
