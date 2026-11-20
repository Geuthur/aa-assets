"""Assets model: an item of an owner at a location."""

# Django
from django.db import models
from django.utils.translation import gettext_lazy as _

# Alliance Auth (External Libs)
from eve_sde.models.types import ItemType

# AA Assets
from assets.managers.assets import AssetsManager
from assets.models.location import Location


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
        "Owner",
        on_delete=models.CASCADE,
        related_name="assets",
        help_text="Corporation that owns the asset",
    )
    eve_type = models.ForeignKey(
        ItemType, on_delete=models.CASCADE, related_name="+", help_text="asset type"
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
