# Standard Library
from datetime import timedelta
from http import HTTPStatus
from unittest.mock import MagicMock

# Third Party
from aiopenapi3 import RequestError

# Django
from django.utils import timezone

# Alliance Auth
from esi.errors import TokenError
from esi.exceptions import (
    ESIBucketLimitException,
    ESIErrorLimitException,
    HTTPClientError,
    HTTPNotModified,
    HTTPServerError,
)
from esi.rate_limiting import ESIRateLimitBucket

# AA Assets
from assets.errors import DownTimeError
from assets.models.helpers.update_manager import (
    OwnerUpdateSection,
    UpdateSectionResult,
)
from assets.models.owner import Owner, OwnerUpdateStatus
from assets.tests import AuthTestCase
from assets.tests.testdata.owner import OwnerUpdateStatusFactory


class TestUpdateManager(AuthTestCase):
    """Unit tests for UpdateManager and update status behavior."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner = Owner.objects.create(
            character=cls.user.profile.main_character.character_ownership
        )
        cls.manager = cls.owner.update_manager

    def test_need_update_should_return_false_when_has_token_error(self):
        # Test Data
        status = OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            has_token_error=True,
            last_run_finished_at=timezone.now() - timedelta(hours=5),
        )

        # Test Action
        needs_update = status.need_update()

        # Expected Result
        self.assertFalse(needs_update)

    def test_need_update_should_return_true_when_never_run(self):
        # Test Data
        status = OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            has_token_error=False,
            last_run_finished_at=None,
        )

        # Test Action
        needs_update = status.need_update()

        # Expected Result
        self.assertTrue(needs_update)

    def test_need_update_should_return_false_when_within_stale_time(self):
        # Test Data: assets are stale after 60 minutes, run 10 minutes ago
        status = OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            has_token_error=False,
            last_run_finished_at=timezone.now() - timedelta(minutes=10),
        )

        # Test Action
        needs_update = status.need_update()

        # Expected Result
        self.assertFalse(needs_update)

    def test_need_update_should_return_true_when_beyond_stale_time(self):
        # Test Data: assets are stale after 60 minutes, run 70 minutes ago
        status = OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            has_token_error=False,
            last_run_finished_at=timezone.now() - timedelta(minutes=70),
        )

        # Test Action
        needs_update = status.need_update()

        # Expected Result
        self.assertTrue(needs_update)

    def test_update_section_if_changed_should_handle_http_304_not_modified(self):
        # Test Data
        def mock_fetch(owner, force_refresh):
            raise HTTPNotModified(HTTPStatus.NOT_MODIFIED, {})

        # Test Action
        result = self.manager.update_section_if_changed(
            section=OwnerUpdateSection.ASSETS,
            fetch_func=mock_fetch,
            force_refresh=False,
        )

        # Expected Result
        self.assertFalse(result.is_changed)
        self.assertFalse(result.is_updated)
        self.assertFalse(result.has_token_error)
        self.assertEqual(result.error_message, "")

    def test_update_section_if_changed_should_set_token_error_on_http_403(self):
        # Test Data
        def mock_fetch(owner, force_refresh):
            raise HTTPClientError(HTTPStatus.FORBIDDEN, {}, b"Forbidden")

        # Test Action
        result = self.manager.update_section_if_changed(
            section=OwnerUpdateSection.ASSETS,
            fetch_func=mock_fetch,
            force_refresh=False,
        )

        # Expected Result
        self.assertFalse(result.is_changed)
        self.assertFalse(result.is_updated)
        self.assertTrue(result.has_token_error)
        self.assertIn("HTTPClientError (403)", result.error_message)

    def test_update_section_if_changed_should_not_set_token_error_on_http_400(self):
        # Test Data
        def mock_fetch(owner, force_refresh):
            raise HTTPClientError(HTTPStatus.BAD_REQUEST, {}, b"Bad Request")

        # Test Action
        result = self.manager.update_section_if_changed(
            section=OwnerUpdateSection.ASSETS,
            fetch_func=mock_fetch,
            force_refresh=False,
        )

        # Expected Result
        self.assertFalse(result.is_changed)
        self.assertFalse(result.is_updated)
        self.assertFalse(result.has_token_error)
        self.assertIn("HTTPClientError (400)", result.error_message)

    def test_update_section_if_changed_should_raise_token_error(self):
        # Test Data
        def mock_fetch(owner, force_refresh):
            raise TokenError("Token expired")

        # Test Action & Expected Result: execute_section catches it one level up
        with self.assertRaises(TokenError):
            self.manager.update_section_if_changed(
                section=OwnerUpdateSection.ASSETS,
                fetch_func=mock_fetch,
                force_refresh=False,
            )

    def test_update_section_if_changed_should_return_the_fetched_data(self):
        # Test Data
        def mock_fetch(owner, force_refresh):
            return {"balance": 1}

        # Test Action
        result = self.manager.update_section_if_changed(
            section=OwnerUpdateSection.ASSETS,
            fetch_func=mock_fetch,
            force_refresh=True,
        )

        # Expected Result
        self.assertTrue(result.is_changed)
        self.assertTrue(result.is_updated)
        self.assertEqual(result.data, {"balance": 1})

    def test_perform_update_status_should_catch_token_error_without_raising(self):
        # Test Data
        mock_method = MagicMock(side_effect=TokenError("Token expired"))

        # Test Action
        result = self.manager.perform_update_status(
            section=OwnerUpdateSection.ASSETS,
            method=mock_method,
        )

        # Expected Result
        self.assertFalse(result.is_changed)
        self.assertFalse(result.is_updated)
        self.assertTrue(result.has_token_error)
        self.assertIn("TokenError: Token expired", result.error_message)

    def test_perform_update_status_should_catch_server_error_without_token_error(self):
        # Test Data
        mock_method = MagicMock(
            side_effect=HTTPServerError(
                HTTPStatus.INTERNAL_SERVER_ERROR, {}, b"Internal Server Error"
            )
        )

        # Test Action
        result = self.manager.perform_update_status(
            section=OwnerUpdateSection.ASSETS,
            method=mock_method,
        )

        # Expected Result
        self.assertFalse(result.is_changed)
        self.assertFalse(result.is_updated)
        self.assertFalse(result.has_token_error)
        self.assertIn("500", result.error_message)

    def test_perform_update_status_should_raise_retryable_esi_errors(self):
        for exc in retryable_errors():
            with self.subTest(exc=type(exc).__name__):
                # Test Data
                mock_method = MagicMock(side_effect=exc)

                # Test Action & Expected Result
                with self.assertRaises(type(exc)) as ctx:
                    self.manager.perform_update_status(
                        section=OwnerUpdateSection.ASSETS,
                        method=mock_method,
                    )
                self.assertIs(ctx.exception, exc)

    def test_update_section_if_changed_should_raise_retryable_esi_errors(self):
        for exc in retryable_errors():
            with self.subTest(exc=type(exc).__name__):
                # Test Data
                fetch_func = MagicMock(side_effect=exc)

                # Test Action & Expected Result
                with self.assertRaises(type(exc)):
                    self.manager.update_section_if_changed(
                        section=OwnerUpdateSection.ASSETS,
                        fetch_func=fetch_func,
                    )

    def test_perform_update_status_should_catch_unexpected_error(self):
        # Test Data
        mock_method = MagicMock(side_effect=ValueError("boom"))

        # Test Action
        result = self.manager.perform_update_status(
            section=OwnerUpdateSection.ASSETS,
            method=mock_method,
        )

        # Expected Result
        self.assertFalse(result.has_token_error)
        self.assertEqual(result.error_message, "ValueError: boom")

    def test_update_section_log_should_record_success_on_http_304(self):
        # Test Data
        result_304 = UpdateSectionResult(
            is_changed=False,
            is_updated=False,
            has_token_error=False,
            error_message="",
        )

        # Test Action
        self.manager.update_section_log(
            section=OwnerUpdateSection.ASSETS,
            result=result_304,
        )

        # Expected Result
        status = OwnerUpdateStatus.objects.get(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
        )
        self.assertTrue(status.is_success)
        self.assertFalse(status.has_token_error)
        self.assertEqual(status.error_message, "")
        self.assertIsNotNone(status.last_run_finished_at)

    def test_update_section_log_should_record_errors(self):
        # Test Data
        result = UpdateSectionResult(
            is_changed=False,
            is_updated=False,
            has_token_error=True,
            error_message="TokenError: expired",
        )

        # Test Action
        self.manager.update_section_log(
            section=OwnerUpdateSection.ASSETS, result=result
        )

        # Expected Result
        status = OwnerUpdateStatus.objects.get(
            owner=self.owner, section=OwnerUpdateSection.ASSETS
        )
        self.assertFalse(status.is_success)
        self.assertTrue(status.has_token_error)
        self.assertEqual(status.error_message, "TokenError: expired")

    def test_get_sections_to_update_force_refresh_should_return_all(self):
        # Test Data
        OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            has_token_error=True,
        )

        # Test Action
        sections = self.manager.get_sections_to_update(force_refresh=True)

        # Expected Result
        self.assertEqual(sections, OwnerUpdateSection.get_sections())
        status = OwnerUpdateStatus.objects.get(
            owner=self.owner, section=OwnerUpdateSection.ASSETS
        )
        self.assertFalse(status.has_token_error)

    def test_get_sections_to_update_should_return_stale_sections(self):
        # Test Data
        OwnerUpdateStatus.objects.filter(owner=self.owner).delete()

        # Test Action
        sections = self.manager.get_sections_to_update(force_refresh=False)

        # Expected Result
        self.assertEqual(sections, OwnerUpdateSection.get_sections())

    def test_get_sections_to_update_should_skip_fresh_sections(self):
        # Test Data
        OwnerUpdateStatusFactory(
            owner=self.owner,
            section=OwnerUpdateSection.ASSETS,
            last_run_finished_at=timezone.now(),
        )

        # Test Action
        sections = self.manager.get_sections_to_update(force_refresh=False)

        # Expected Result
        self.assertEqual(sections, [])

    def test_execute_section_should_call_owner_method_and_log_success(self):
        # Test Data
        expected_result = UpdateSectionResult(
            is_changed=True,
            is_updated=True,
            has_token_error=False,
            error_message="",
            data={"test": "data"},
        )
        self.owner.update_assets = MagicMock(return_value=expected_result)

        # Test Action
        result = self.manager.execute_section(
            OwnerUpdateSection.ASSETS, force_refresh=True
        )

        # Expected Result
        self.assertEqual(result, expected_result)
        self.owner.update_assets.assert_called_once()
        status = OwnerUpdateStatus.objects.get(
            owner=self.owner, section=OwnerUpdateSection.ASSETS
        )
        self.assertTrue(status.is_success)
        self.assertFalse(status.has_token_error)
        self.assertIsNotNone(status.last_update_finished_at)

    def test_execute_section_should_accept_the_section_value_and_pass_force_refresh(
        self,
    ):
        # Test Data
        calls = []

        def update_assets(force_refresh: bool = False):
            calls.append(force_refresh)
            return UpdateSectionResult(is_changed=False, is_updated=False)

        self.owner.update_assets = update_assets

        # Test Action
        self.manager.execute_section("assets")
        self.manager.execute_section("assets", force_refresh=True)

        # Expected Result
        self.assertEqual(calls, [False, True])

    def test_execute_section_should_record_and_raise_retryable_esi_errors(self):
        for exc in retryable_errors():
            with self.subTest(exc=type(exc).__name__):
                # Test Data
                self.owner.update_assets = MagicMock(side_effect=exc)

                # Test Action
                with self.assertRaises(type(exc)):
                    self.manager.execute_section(OwnerUpdateSection.ASSETS)

                # Expected Result: a failed run, not success and not in progress
                status = OwnerUpdateStatus.objects.get(
                    owner=self.owner, section=OwnerUpdateSection.ASSETS
                )
                self.assertFalse(status.is_success)
                self.assertFalse(status.has_token_error)
                self.assertTrue(status.error_message.startswith(type(exc).__name__))
                self.assertIsNotNone(status.last_run_finished_at)
                self.assertTrue(status.need_update())

    def test_mixin_provides_update_manager_and_shortcuts(self):
        # Test Action & Expected Result
        self.assertIsNotNone(self.owner.update_manager)
        self.assertEqual(self.owner.update_manager.owner, self.owner)
        sections = self.owner.get_sections_to_update(force_refresh=True)
        self.assertEqual(sections, OwnerUpdateSection.get_sections())


class TestUpdateSection(AuthTestCase):
    def test_section_should_name_the_update_method(self):
        # Test Action & Expected Result
        self.assertEqual(OwnerUpdateSection.ASSETS.method_name, "update_assets")
        self.assertEqual(OwnerUpdateSection.get_sections(), ["assets"])


def retryable_errors() -> list[Exception]:
    """Errors on which `retry_task_on_esi_error` retries the task."""
    return [
        ESIErrorLimitException(reset=60),
        ESIBucketLimitException(ESIRateLimitBucket("char-assets:1", 150, 900), 60),
        HTTPServerError(HTTPStatus.BAD_GATEWAY, {}, b"Bad Gateway"),
        HTTPServerError(HTTPStatus.SERVICE_UNAVAILABLE, {}, b"Service Unavailable"),
        HTTPServerError(HTTPStatus.GATEWAY_TIMEOUT, {}, b"Gateway Timeout"),
        RequestError(
            operation=None, request=None, data="Request failed", parameters={}
        ),
        DownTimeError("ESI is in daily downtime"),
    ]
