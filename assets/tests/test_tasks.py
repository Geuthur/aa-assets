"""Tests for the ESI error handling of the tasks."""

# Standard Library
from http import HTTPStatus
from unittest.mock import MagicMock, patch

# Third Party
import pook
from aiopenapi3 import RequestError
from celery.exceptions import Retry
from evesde_factory.allianceauth import EveCorporationInfoFactory
from evesde_factory.eve_sde import ItemTypeFactory, NPCStationFactory

# Django
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

# Alliance Auth
from esi.exceptions import ESIErrorLimitException, HTTPServerError

# AA Assets
from assets import tasks
from assets.errors import DownTimeError
from assets.managers.assets import (
    build_market_price_cache_tag,
    set_market_price_cache,
)
from assets.models import (
    Assets,
    Location,
    Owner,
    OwnerUpdateStatus,
    Request,
    RequestAssets,
)
from assets.models.helpers.update_manager import (
    OwnerUpdateSection,
    UpdateSectionResult,
)
from assets.providers import DOWNTIME_TIMER
from assets.task_helpers.location_helpers import get_cache_key
from assets.tests import AuthTestCase
from assets.tests.testdata.esi_urls import (
    character_assets_url,
    clear_esi_limits,
    corporation_assets_url,
    structure_url,
    universe_names_url,
)
from assets.tests.testdata.factory import UserMainFactory
from assets.tests.testdata.owner import OwnerUpdateStatusFactory

STATION_ID = 60003760
STRUCTURE_ID = 1_000_000_000_001
LOCATION_ID = 1_000_000_000_002
SERVER_ERRORS = [
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
]


class EsiTaskTestCase(AuthTestCase):
    """Owner of the main character and clean ESI limits for every test."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        esi_user = UserMainFactory()
        cls.character = esi_user.profile.main_character
        cls.owner = Owner.objects.create(character=cls.character.character_ownership)

    def setUp(self):
        super().setUp()
        clear_esi_limits()
        self.addCleanup(clear_esi_limits)

    def _assert_retried(self, mock_retry, exc_type, countdown_min: float):
        mock_retry.assert_called_once()
        kwargs = mock_retry.call_args.kwargs
        self.assertIsInstance(kwargs["exc"], exc_type)
        self.assertGreaterEqual(kwargs["countdown"], countdown_min)

    def _error_limit(self, url: str):
        pook.get(
            url,
            reply=420,
            response_json={"error": "Error limited"},
            response_headers={"X-RateLimit-Reset": "30"},
        )


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_assets_for_owner, "retry", side_effect=Retry)
class TestUpdateAssetsForOwner(EsiTaskTestCase):
    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.get(
                    character_assets_url(self.character.character_id),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        self._error_limit(character_assets_url(self.character.character_id))

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)

    @pook.on
    @patch("esi.app_settings.ESI_SERVER_ERROR_MAX_RETRIES", 1)
    def test_should_retry_on_request_errors(self, mock_retry):
        # Test Data
        pook.get(character_assets_url(self.character.character_id)).error(
            ConnectionError("Connection reset")
        )

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        self._assert_retried(mock_retry, RequestError, DOWNTIME_TIMER)

    @pook.on
    def test_should_not_retry_on_esi_client_errors(self, mock_retry):
        # Test Data
        pook.get(
            character_assets_url(self.character.character_id),
            reply=HTTPStatus.NOT_FOUND,
            response_json={"error": "Not found"},
        )

        # Test Action
        tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result: the error ends in the update status of the section
        mock_retry.assert_not_called()
        status = OwnerUpdateStatus.objects.get(
            owner=self.owner, section=OwnerUpdateSection.ASSETS
        )
        self.assertFalse(status.is_success)
        self.assertTrue(status.error_message.startswith("HTTPClientError (404)"))

    @override_settings(DISABLE_DAILY_DOWNTIME_CHECK=False)
    @patch(tasks.__name__ + ".Owner.execute_section", autospec=True)
    def test_should_retry_during_daily_downtime(self, mock_update, mock_retry):
        # Test Data
        with patch("assets.providers.timezone.now") as mock_now:
            mock_now.return_value = timezone.datetime.strptime("11:05", "%H:%M")

            # Test Action
            with self.assertRaises(Retry):
                tasks.update_assets_for_owner(self.owner.pk)

        # Expected Result
        self._assert_retried(mock_retry, DownTimeError, DOWNTIME_TIMER)
        mock_update.assert_not_called()


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_location, "retry", side_effect=Retry)
class TestUpdateLocation(EsiTaskTestCase):
    """The station comes from the SDE, only its name is fetched from ESI."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        NPCStationFactory(id=STATION_ID, name="")

    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.post(
                    universe_names_url(),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    tasks.update_location(STATION_ID)

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        pook.post(
            universe_names_url(),
            reply=420,
            response_json={"error": "Error limited"},
            response_headers={"X-RateLimit-Reset": "30"},
        )

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_location(STATION_ID)

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)

    @pook.on
    def test_should_save_station_with_name_from_esi(self, mock_retry):
        # Test Data
        pook.post(
            universe_names_url(),
            json=[STATION_ID],
            reply=HTTPStatus.OK,
            response_json=[
                {"id": STATION_ID, "name": "Jita IV - Moon 4", "category": "station"}
            ],
        )

        # Test Action
        tasks.update_location(STATION_ID)

        # Expected Result
        mock_retry.assert_not_called()
        location = Location.objects.get(id=STATION_ID)
        self.assertEqual(location.name, "Jita IV - Moon 4")


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_parent_location, "retry", side_effect=Retry)
class TestUpdateParentLocation(EsiTaskTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Location.objects.create(id=LOCATION_ID)

    def setUp(self):
        super().setUp()
        cache.delete(get_cache_key(STRUCTURE_ID))
        self.addCleanup(cache.delete, get_cache_key(STRUCTURE_ID))

    def _run(self):
        tasks.update_parent_location(
            LOCATION_ID,
            STRUCTURE_ID,
            self.character.character_id,
            35832,
            force_refresh=True,
        )

    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.get(
                    structure_url(STRUCTURE_ID),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    self._run()

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        self._error_limit(structure_url(STRUCTURE_ID))

        # Test Action
        with self.assertRaises(Retry):
            self._run()

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)

    @pook.on
    def test_should_cache_forbidden_structures_without_retry(self, mock_retry):
        # Test Data
        pook.get(
            structure_url(STRUCTURE_ID),
            reply=HTTPStatus.FORBIDDEN,
            response_json={"error": "Forbidden"},
        )

        # Test Action
        self._run()

        # Expected Result
        mock_retry.assert_not_called()
        self.assertEqual(cache.get(get_cache_key(STRUCTURE_ID)), 1)
        self.assertIsNone(Location.objects.get(id=LOCATION_ID).parent)


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch.object(tasks.update_all_parent_locations, "retry", side_effect=Retry)
class TestUpdateAllParentLocations(EsiTaskTestCase):
    def test_should_retry_on_esi_server_errors(self, mock_retry):
        for status_code in SERVER_ERRORS:
            with self.subTest(status_code=status_code), pook.use():
                # Test Data
                mock_retry.reset_mock()
                pook.get(
                    character_assets_url(self.character.character_id),
                    reply=status_code,
                    response_json={"error": status_code.phrase},
                )

                # Test Action
                with self.assertRaises(Retry):
                    tasks.update_all_parent_locations(force_refresh=True)

                # Expected Result
                self._assert_retried(mock_retry, HTTPServerError, DOWNTIME_TIMER)

    @pook.on
    def test_should_retry_on_the_esi_error_limit(self, mock_retry):
        # Test Data
        self._error_limit(character_assets_url(self.character.character_id))

        # Test Action
        with self.assertRaises(Retry):
            tasks.update_all_parent_locations(force_refresh=True)

        # Expected Result
        self._assert_retried(mock_retry, ESIErrorLimitException, 30)


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
class TestUpdateAssetsForOwnerOrders(EsiTaskTestCase):
    """Open orders are linked to the new assets of their own owner only."""

    ITEM_ID = 1_000_000_000_100

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_owner = Owner.objects.create(
            character=UserMainFactory().profile.main_character.character_ownership
        )
        cls.location = Location.objects.create(id=STATION_ID, name="Jita IV - Moon 4")
        cls.eve_type = ItemTypeFactory()

    def setUp(self):
        super().setUp()
        set_market_price_cache(self.eve_type.id, 5.0)
        self.addCleanup(cache.delete, build_market_price_cache_tag(self.eve_type.id))
        self.request = Request.objects.create(
            requesting_user=self.user, status=Request.STATUS_OPEN
        )

    def _asset(self, owner: Owner) -> Assets:
        return Assets.objects.create(
            item_id=self.ITEM_ID,
            owner=owner,
            eve_type=self.eve_type,
            location=self.location,
            location_flag=Assets.LocationFlag.HANGAR,
            location_type="station",
            quantity=10,
            singleton=False,
            blueprint_copy=False,
        )

    def _order(self, asset_pk: int) -> RequestAssets:
        return RequestAssets.objects.create(
            name=self.eve_type.name,
            request=self.request,
            asset_pk=asset_pk,
            asset_location_id=self.location.id,
            asset_location_flag=Assets.LocationFlag.HANGAR,
            eve_type=self.eve_type,
            quantity=1,
        )

    def _esi_assets(self):
        pook.get(
            character_assets_url(self.character.character_id),
            reply=200,
            response_json=[
                {
                    "is_blueprint_copy": False,
                    "is_singleton": False,
                    "item_id": self.ITEM_ID,
                    "location_flag": "Hangar",
                    "location_id": self.location.id,
                    "location_type": "station",
                    "quantity": 10,
                    "type_id": self.eve_type.id,
                }
            ],
        )

    @pook.on
    def test_should_link_own_order_when_another_owner_has_the_same_asset(self):
        # Test Data: both owners hold the same type at the same place
        order = self._order(self._asset(self.owner).pk)
        other_asset = self._asset(self.other_owner)
        other_order = self._order(other_asset.pk)
        self._esi_assets()

        # Test Action
        tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        new_asset = Assets.objects.get(owner=self.owner)
        order.refresh_from_db()
        other_order.refresh_from_db()
        self.assertEqual(order.asset_pk, new_asset.pk)
        self.assertEqual(other_order.asset_pk, other_asset.pk)

    @pook.on
    def test_should_link_orders_without_existing_asset(self):
        # Test Data: the asset of the order is gone, e.g. after an earlier update
        lost_asset = self._asset(self.owner)
        order = self._order(lost_asset.pk)
        lost_asset.delete()
        self._esi_assets()

        # Test Action
        tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        order.refresh_from_db()
        self.assertEqual(order.asset_pk, Assets.objects.get(owner=self.owner).pk)

    @pook.on
    def test_should_not_touch_orders_of_existing_assets_of_other_owners(self):
        # Test Data: the other owner holds the asset in another hangar
        other_asset = self._asset(self.other_owner)
        other_order = self._order(other_asset.pk)
        self._esi_assets()

        # Test Action
        tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        other_order.refresh_from_db()
        self.assertEqual(other_order.asset_pk, other_asset.pk)

    @pook.on
    def test_should_update_owners_without_status_and_record_success(self):
        # Test Data: an owner from before the update status has no status row
        self._esi_assets()

        # Test Action
        result = tasks.update_assets_for_owner(self.owner.pk)

        # Expected Result
        self.assertTrue(result)
        self.assertEqual(Assets.objects.filter(owner=self.owner).count(), 1)
        status = OwnerUpdateStatus.objects.get(
            owner=self.owner, section=OwnerUpdateSection.ASSETS
        )
        self.assertTrue(status.is_success)
        self.assertIsNotNone(status.last_update_finished_at)

    @pook.on
    def test_should_remove_old_assets_on_empty_esi_response(self):
        # Test Data: the owner sold or moved everything
        self._asset(self.owner)
        other_asset = self._asset(self.other_owner)
        pook.get(
            character_assets_url(self.character.character_id),
            reply=200,
            response_json=[],
        )

        # Test Action
        result = tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        self.assertTrue(result)
        self.assertFalse(Assets.objects.filter(owner=self.owner).exists())
        self.assertTrue(Assets.objects.filter(pk=other_asset.pk).exists())
        status = OwnerUpdateStatus.objects.get(
            owner=self.owner, section=OwnerUpdateSection.ASSETS
        )
        self.assertTrue(status.is_success)

    @pook.on
    def test_should_fetch_corporation_assets(self):
        # Test Data
        corporation = EveCorporationInfoFactory()
        owner = Owner.objects.create(
            corporation=corporation, character=self.character.character_ownership
        )
        pook.get(
            corporation_assets_url(corporation.corporation_id),
            reply=200,
            response_json=[
                {
                    "is_blueprint_copy": False,
                    "is_singleton": False,
                    "item_id": self.ITEM_ID,
                    "location_flag": "Hangar",
                    "location_id": self.location.id,
                    "location_type": "station",
                    "quantity": 3,
                    "type_id": self.eve_type.id,
                }
            ],
        )

        # Test Action
        tasks.update_assets_for_owner(owner.pk, force_refresh=True)

        # Expected Result
        asset = Assets.objects.get(owner=owner)
        self.assertEqual(asset.quantity, 3)
        self.assertEqual(asset.price, 5.0)


@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
@patch(tasks.__name__ + ".update_assets_for_owner", spec=True)
class TestUpdateAllAssets(EsiTaskTestCase):
    def test_should_queue_active_owners_only(self, mock_update):
        # Test Data: also owners with a fresh update status are queued
        OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            last_run_finished_at=timezone.now(),
        )
        Owner.objects.create(corporation=EveCorporationInfoFactory(), is_active=False)

        # Test Action
        count = tasks.update_all_assets(force_refresh=True)

        # Expected Result
        self.assertEqual(count, 1)
        mock_update.apply_async.assert_called_once_with(
            args=[self.owner.pk], kwargs={"force_refresh": True}, priority=6
        )


@override_settings(
    CELERY_ALWAYS_EAGER=True,
    CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
    DISABLE_DAILY_DOWNTIME_CHECK=True,
)
@patch(tasks.__name__ + ".Owner.execute_section", autospec=True)
class TestUpdateAssetsForOwnerSections(EsiTaskTestCase):
    def test_should_execute_stale_sections(self, mock_execute_section):
        # Test Data
        mock_execute_section.return_value = UpdateSectionResult(
            is_changed=True, is_updated=True
        )

        # Test Action
        result = tasks.update_assets_for_owner(self.owner.pk)

        # Expected Result
        self.assertTrue(result)
        mock_execute_section.assert_called_once_with(
            self.owner, OwnerUpdateSection.ASSETS.value, force_refresh=False
        )

    def test_should_skip_fresh_sections(self, mock_execute_section):
        # Test Data
        OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            last_run_finished_at=timezone.now(),
        )

        # Test Action
        result = tasks.update_assets_for_owner(self.owner.pk)

        # Expected Result
        self.assertFalse(result)
        mock_execute_section.assert_not_called()

    def test_should_force_refresh_every_section(self, mock_execute_section):
        # Test Data
        OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            last_run_finished_at=timezone.now(),
        )

        # Test Action
        result = tasks.update_assets_for_owner(self.owner.pk, force_refresh=True)

        # Expected Result
        self.assertTrue(result)
        mock_execute_section.assert_called_once_with(
            self.owner, OwnerUpdateSection.ASSETS.value, force_refresh=True
        )

    def test_should_return_false_for_unknown_owner(self, mock_execute_section):
        # Test Action & Expected Result
        self.assertFalse(tasks.update_assets_for_owner(999999))
        mock_execute_section.assert_not_called()

    @patch(tasks.__name__ + ".retry_task_on_esi_error")
    def test_should_run_the_sections_inside_the_retry_context(
        self, mock_retry, _mock_execute_section
    ):
        # Test Data
        mock_retry.return_value.__enter__ = MagicMock()
        mock_retry.return_value.__exit__ = MagicMock(return_value=False)

        # Test Action
        tasks.update_assets_for_owner(self.owner.pk)

        # Expected Result
        mock_retry.assert_called_once()
        mock_retry.return_value.__enter__.assert_called_once()
