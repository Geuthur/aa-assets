"""Tests for the Location manager."""

# Standard Library
from http import HTTPStatus

# Third Party
import pook
from evesde_factory.eve_sde import NPCStationFactory

# Alliance Auth (External Libs)
from eve_sde.models.map import NPCStation

# AA Assets
from assets.models import EveEntity, Location
from assets.tests import NoSocketsTestCase
from assets.tests.testdata.esi_urls import clear_esi_limits, universe_names_url

STATION_ID = 60_003_760
OWNER_ID = 1_000_035


class TestUpdateOrCreateEsiStation(NoSocketsTestCase):
    def setUp(self):
        super().setUp()
        clear_esi_limits()
        self.addCleanup(clear_esi_limits)

    @pook.on
    def test_should_create_station_from_sde_with_name_from_esi(self):
        # Test Data: the SDE holds no station names, the name comes from ESI
        station = NPCStationFactory(id=STATION_ID, name="", owner_id_raw=OWNER_ID)
        EveEntity.objects.create(
            id=OWNER_ID, name="Caldari Navy", category=EveEntity.CATEGORY_CORPORATION
        )
        names_mock = pook.post(
            universe_names_url(),
            json=[STATION_ID],
            reply=HTTPStatus.OK,
            response_json=[
                {
                    "id": STATION_ID,
                    "name": "Jita IV - Moon 4 - Caldari Navy Assembly Plant",
                    "category": "station",
                }
            ],
        )

        # Test Action
        location, created = Location.objects.update_or_create_esi(
            location_id=STATION_ID
        )

        # Expected Result
        self.assertTrue(created)
        self.assertTrue(names_mock.isdone())
        self.assertEqual(
            location.name, "Jita IV - Moon 4 - Caldari Navy Assembly Plant"
        )
        self.assertEqual(location.eve_solar_system, station.solar_system)
        self.assertEqual(location.eve_type, station.item_type)
        self.assertEqual(location.owner_id, OWNER_ID)

    @pook.on
    def test_should_raise_for_station_unknown_to_sde(self):
        # Test Data
        names_mock = pook.post(universe_names_url(), reply=HTTPStatus.OK, persist=True)

        # Test Action
        with self.assertRaises(NPCStation.DoesNotExist):
            Location.objects.update_or_create_esi(location_id=STATION_ID)

        # Expected Result
        self.assertEqual(names_mock.calls, 0)
        self.assertFalse(Location.objects.filter(id=STATION_ID).exists())
