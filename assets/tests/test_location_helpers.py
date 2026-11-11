"""Tests for the location helpers."""

# Standard Library
from http import HTTPStatus

# Third Party
import pook
from evesde_factory.eve_sde import SolarSystemFactory

# Django
from django.core.cache import cache

# AA Assets
from assets.task_helpers.location_helpers import (
    fetch_location,
    fetch_parent_location,
    get_cache_key,
    get_location_type,
)
from assets.tests import AuthTestCase
from assets.tests.testdata.esi_urls import clear_esi_limits, structure_url

SOLAR_SYSTEM_ID = 30_000_142
STRUCTURE_ID = 1_000_000_000_001


class TestGetLocationType(AuthTestCase):
    def test_should_return_location_for_solar_system(self):
        # Test Data
        system = SolarSystemFactory(id=SOLAR_SYSTEM_ID, name="Jita")

        # Test Action
        location, existing_location = get_location_type(SOLAR_SYSTEM_ID)

        # Expected Result
        self.assertEqual(location.id, SOLAR_SYSTEM_ID)
        self.assertEqual(location.name, "Jita")
        self.assertEqual(location.eve_solar_system, system)
        self.assertIsNone(existing_location)

    def test_should_return_no_location_for_unknown_solar_system(self):
        # Test Action
        location, existing_location = get_location_type(SOLAR_SYSTEM_ID)

        # Expected Result
        self.assertIsNone(location)
        self.assertIsNone(existing_location)


class TestFetchLocation(AuthTestCase):
    def setUp(self):
        super().setUp()
        clear_esi_limits()
        self.addCleanup(clear_esi_limits)
        cache.delete(get_cache_key(STRUCTURE_ID))
        self.addCleanup(cache.delete, get_cache_key(STRUCTURE_ID))

    def _structure_reply(self):
        pook.get(
            structure_url(STRUCTURE_ID),
            reply=HTTPStatus.OK,
            response_json={
                "name": "Test Structure",
                "owner_id": 98000001,
                "solar_system_id": SOLAR_SYSTEM_ID,
                "type_id": 35832,
            },
        )

    @pook.on
    def test_should_return_structure_location(self):
        # Test Data
        SolarSystemFactory(id=SOLAR_SYSTEM_ID)
        self._structure_reply()

        # Test Action
        location = fetch_location(
            STRUCTURE_ID, None, self.user.profile.main_character.character_id
        )

        # Expected Result
        self.assertEqual(location.id, STRUCTURE_ID)
        self.assertEqual(location.name, "Test Structure")
        self.assertEqual(location.eve_solar_system_id, SOLAR_SYSTEM_ID)

    @pook.on
    def test_should_return_none_for_unknown_solar_system(self):
        # Test Data
        self._structure_reply()

        # Test Action
        location = fetch_location(
            STRUCTURE_ID, None, self.user.profile.main_character.character_id
        )

        # Expected Result
        self.assertIsNone(location)

    @pook.on
    def test_should_not_fetch_structure_for_unknown_solar_system_id(self):
        # Test Data
        structure_mock = pook.get(
            structure_url(SOLAR_SYSTEM_ID), reply=HTTPStatus.OK, persist=True
        )

        # Test Action
        location = fetch_location(
            SOLAR_SYSTEM_ID, None, self.user.profile.main_character.character_id
        )

        # Expected Result
        self.assertIsNone(location)
        self.assertEqual(structure_mock.calls, 0)


class TestFetchParentLocation(AuthTestCase):
    def setUp(self):
        super().setUp()
        clear_esi_limits()
        self.addCleanup(clear_esi_limits)
        cache.delete(get_cache_key(STRUCTURE_ID))
        self.addCleanup(cache.delete, get_cache_key(STRUCTURE_ID))

    def _structure_reply(self):
        pook.get(
            structure_url(STRUCTURE_ID),
            reply=HTTPStatus.OK,
            response_json={
                "name": "Test Structure",
                "owner_id": 98000001,
                "solar_system_id": SOLAR_SYSTEM_ID,
                "type_id": 35832,
            },
        )

    @pook.on
    def test_should_return_structure_location(self):
        # Test Data
        SolarSystemFactory(id=SOLAR_SYSTEM_ID)
        self._structure_reply()

        # Test Action
        location = fetch_parent_location(
            STRUCTURE_ID, self.user.profile.main_character.character_id
        )

        # Expected Result
        self.assertEqual(location.id, STRUCTURE_ID)
        self.assertEqual(location.name, "Test Structure")
        self.assertEqual(location.eve_solar_system_id, SOLAR_SYSTEM_ID)

    @pook.on
    def test_should_return_none_for_unknown_solar_system(self):
        # Test Data
        self._structure_reply()

        # Test Action
        location = fetch_parent_location(
            STRUCTURE_ID, self.user.profile.main_character.character_id
        )

        # Expected Result
        self.assertIsNone(location)

    @pook.on
    def test_should_not_fetch_structure_for_unknown_solar_system_id(self):
        # Test Data
        structure_mock = pook.get(
            structure_url(SOLAR_SYSTEM_ID), reply=HTTPStatus.OK, persist=True
        )

        # Test Action
        location = fetch_parent_location(
            SOLAR_SYSTEM_ID, self.user.profile.main_character.character_id
        )

        # Expected Result
        self.assertIsNone(location)
        self.assertEqual(structure_mock.calls, 0)
