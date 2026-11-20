# Changelog

## [In Development] - Unreleased

<!--
> [!NOTE]
>

> [!TIP]
>

> [!IMPORTANT]
>

> [!WARNING]
>

> [!CAUTION]
>

Section Order:

### Added
### Fixed
### Changed
### Removed
-->

<!-- Your changes go here -->

> [!IMPORTANT]
> Basic access is only granted by `basic_access`. Users with higher permissions (`corporation_access`, `manage_requests`, `manage_corporation`, `admin_access`) but without `basic_access` lose access to the API and to the pages to add a corporation and to complete or reopen requests. Grant `basic_access` to these users or groups.

### Fixed

- The asset update links open orders only to the new assets of their own owner (orders whose asset is gone are linked again too); before, it took the open orders of all owners and stopped with `MultipleObjectsReturned` when two assets matched an order
- The ESI operation `PostUniverseNames` is added to `__operations__`; without it the ESI client did not know the operation and resolving an unknown station owner (`EveEntity` manager) crashed the asset update with an `AttributeError`
- The order notification texts in `Request` (new request, completed, canceled, reopened) are filled with `.format()` instead of f-strings inside `_()`, so they can be translated; existing translations of the old texts no longer match until Weblate updates them
- The API endpoints `location/` and `location/{location_id}/flag/{location_flag}/` no longer set `auth=None`; the login check of the API applies to them like to all other endpoints
- Development dependencies: `minimatch` 10.2.6 → 11.0.8 (Dependabot alert, DoS via globparts) through `eslint` 10.15.0; the app itself is not affected
- The permission `assets.admin_access` was checked as `assets.admin_Access` in the managers, so it never granted anything to non-superusers; users with `admin_access` now see all assets, locations and requests as the permission text says
- The views `add_corp` and `add_char` required the permissions `assets.add_corporate_owner` and `assets.add_character_owner`, which no longer exist, so only superusers could use them. They now require `manage_corporation` and `basic_access`, like the menu entries that link to them
- `Owner.get_esi_scopes()` is now an instance method and returns the character scopes (`esi-assets.read_assets.v1`) for character owners; before, it always returned the corporation scopes, so character owners asked for a token with the wrong scope
- Solar system locations and structures no longer crash in `get_location_type` and `fetch_location` (`task_helpers/location_helpers.py`): the solar system is looked up with `filter().first()` instead of unpacking the result of `objects.get()`, and an unknown solar system returns `(None, existing_location)` instead of `None`
- `fetch_parent_location` no longer crashes with `SolarSystem.DoesNotExist` when the solar system of a structure is unknown: the solar system is looked up with `filter().first()` and the function returns `None`
- `fetch_location` and `fetch_parent_location` no longer request a structure from ESI when the location ID belongs to an unknown solar system, they return `None`
- `fetch_location` and `fetch_parent_location` no longer request a structure from ESI for a station that ESI answers with `304 Not Modified` while the station is not yet in the database, they return `None`
- `fetch_location` returns the existing location from the database when ESI answers a structure with `304 Not Modified`, like `fetch_parent_location` already did; before, it returned `None`
- Tests no longer share the Redis cache with other processes: `testauth/settings/local.py` gives each test run its own random cache `KEY_PREFIX`. Before, ESI responses cached by a running testauth instance on the same Redis were returned instead of the pook responses. Redis stays the cache backend because Alliance Auth needs `django_redis`
- ESI tasks (`update_assets_for_owner`, `update_location`, `update_parent_location`, `update_all_parent_locations`) now retry on ESI outages and limits through `retry_task_on_esi_error` (HTTP 502/503/504, error limit, bucket limit, request errors, daily downtime)

### Changed

- The asset update of an owner runs through the `UpdateManager` of the app template: a new `OwnerUpdateStatus` keeps success, errors and token errors per owner and section (section `assets`), replacing `Owner.last_update` (migration `0004_owner_update_status`). Existing owners are updated on the next run. New setting `ASSETS_STALE_TYPES` (default: `ASSETS_UPDATE_PERIOD`)
- `models.py` and `managers.py` are split into the packages `assets/models/` and `assets/managers/` (one module per model, like aa-example); imports from `assets.models` and `assets.managers` keep working, no new migration, no change in behavior
- Uniform error format of the API: every error response of an endpoint is an `ErrorSchema` (`{"error": "<text>"}`) instead of a plain string, and every endpoint lists its 403 in the OpenAPI schema. Status codes are unchanged. The order modal shows the message of the API.
- Removed the unreachable `basic_access` checks in `get_requests_statistics` and `get_request_order` and the dead `is None` checks in `get_requests` and `get_my_requests`; the decorator of the API already answers 403
- Every URL of the API requires `basic_access` (403 otherwise). `add_corp`, `mark_request_completed` and `mark_request_open` require it in addition to their own permission, and `add_corp` and `add_char` check the permissions before the SSO step
- The API, the menu hook and the access querysets (`visible_to`, `manage_to`, `visible_eve_characters`) check permissions only through `GeneralManager`; new methods `has_basic_access`, `has_corporation_access`, `has_manage_requests_access` and `has_admin_access` join `has_management_access`. The Django views keep `@permissions_required`. No change in behavior
- `General.Meta.permissions` stays the single place that defines the permissions (plain tuples, texts now translatable); codenames and texts are unchanged and no migration is needed. A new test compares every permission string used in code and templates with it. `General.objects.has_management_access(user)` (`admin_access` or `manage_requests`) replaces the duplicated checks in the `manage_to` querysets
- New test `test_used_permissions_are_defined` checks that every permission string used in code and templates exists in `General.Meta.permissions`
- The `304 Not Modified` branch for stations in `get_location_type` returns `(None, None)` explicitly instead of the always-`None` `existing_location`; no change in behavior
- The Asset Safety (2004) and solar system branches in `get_location_type` return `None` explicitly instead of the always-`None` `existing_location`; no change in behavior
- `get_location_type` returns `None` instead of a QuerySet as second value for locations below 64_000_000 already in the database, matching its type hint; no change in behavior
- Tests of the `EveEntity` manager run against pook responses under the real ESI URL instead of the own ESI client stub; the stub (`esi_stub_openapi.py`, `esi_test_data.json`) is removed
- The station branch in `get_location_type` returns `None` explicitly instead of the always-`None` `existing_location` after fetching the station from ESI; no change in behavior
- Tests of `retry_task_on_esi_error` no longer depend on the time of day, they disable the daily downtime check unless they test it
- `retry_task_on_esi_error` follows the app template: ESI outages retry after `DOWNTIME_TIMER` (10 minutes), the daily downtime (11:00-11:15 UTC) is checked (can be disabled with `DISABLE_DAILY_DOWNTIME_CHECK`), new `is_retryable_esi_error` and `DownTimeError`

### Removed

- Unused `HTTPGatewayTimeoutError` (`assets/errors.py`) and its dead `except` branch in `Owner.update_assets_esi`
- Own HTTP 420 retry in `update_location` and `update_parent_location`: django-esi raises `ESIErrorLimitException` for HTTP 420, so this code path was never reached

### Added

- Python 3.13 Support
- Compatibility to Alliance Auth v5

### Fixed

- Fixed `make coverage` exiting with 0 when tests failed. The reports are still created, and the target now exits with the status of the test run, or with the status of `coverage report` if the tests passed.

### Changed

- The `AppLogger` is created only once in `assets/providers.py`. `managers.py`, `models.py`, `tasks.py`, `api/__init__.py`, `helpers/discord.py` and `task_helpers/location_helpers.py` import it with `from assets.providers import logger` instead of building their own logger; unused loggers in `decorators.py`, `views.py`, `api/helpers.py`, `api/assets/assets.py`, `api/assets/helper.py` and `api/requests/requests.py` were removed, as was the custom `get_extension_logger` in `assets/hooks.py`. Log records now carry the logger name `assets.providers` and the `[Assets]` prefix, and all of them go to the `extensions.assets` logger described in the README (the former `assets/hooks.py` loggers sent them to a separate `assets` logger).
- CI: workflows aligned with the aa-example template (`pypi.yml`, `autotester.yml` with the current Redis action). `.isort.cfg` moved to the repository root. This repository has no `release.yml`.
- Dropped Python 3.10 (end of life): `requires-python` is now `>=3.11`, classifier and tox environment removed, Python 3.10 removed from the CI matrix
- Replaced `pook` with `pookx` in the test dependencies.
- Tests use `add_character_to_user` from `aa-evesde-factory` (new test dependency) instead of a duplicated copy in `assets/tests/testdata/utils.py`; the unused duplicates `dt_eveformat`, `random_string`, `add_new_token` and `add_permission_to_user` were removed.
- Tests create users and characters with `UserMainFactory` (based on `UserFactory` from `aa-evesde-factory`) instead of `create_user_from_evecharacter` and the fixed `allianceauth.json` test data; `load_allianceauth`, `assets/tests/testdata/utils.py` and `assets/tests/testdata/integrations/` were removed.
- Test base class `AssetsTestCase` replaced by `AuthTestCase` with the same layout as in the other apps (`factory`, `user`, `superuser`); the unused extra users and the `_add_character` and `_add_corporation` helpers were removed.
- ESI client loads the OpenAPI spec from a bundled file (`assets/openapi_2026-08-18.json`) instead of downloading it at runtime.
- ESI compatibility date raised from `2026-07-21` to `2026-08-18`.
- Merged `__character_operations__`, `__corporation_operations__` and `__universe_operations__` into a single `__operations__` list in `assets/__init__.py`. The set of ESI operations is unchanged.

### Removed

- Compatibility to Alliance Auth v4
- Dependency `allianceauth-app-utils`

> [!WARNING]
>
> Please note that this release involves structural dependency changes.
> To avoid any service disruptions, it is essential to read the update manual prior to performing the upgrade.

### Update Instructions

After isntalling this version, you need to modify `INSTALLED_APPS` in your `local.py`

```python
INSTALLED_APPS = [
    # other apps
    "eve_sde",  # only if it not already existing
    "assets",
    # other apps?
]

# This line is right below the `INSTALLED_APPS` list, if not already exist!
INSTALLED_APPS = ["modeltranslation"] + INSTALLED_APPS
```

Add the following new task to ensure the SDE data is kept up to date.

```python
if "eve_sde" in INSTALLED_APPS:
    # Run at 12:00 UTC each day
    CELERYBEAT_SCHEDULE["EVE SDE :: Check for SDE Updates"] = {
        "task": "eve_sde.tasks.check_for_sde_updates",
        "schedule": crontab(minute="0", hour="12"),
    }
```

> [!IMPORTANT]
> This is only for installed Assets Enviroment
> You need to have eveuniverse installed during the migration otherwise it will not migrate the old entries.

After running migrations, make sure to run the following commands to import the SDE data into your database.

```shell
python manage.py esde_load_sde
```

Restart your Auth via `supervisor` after running these commands

## [0.2.0] - 2025-11-13

### Added

- Modal System
- Confirm Modal
  - View Order Modal
  - Single Request Modal
  - Multi Request Modal
- Request Statistic API
- Button System
- Request Assets Model
- Permission System
- Notification Send System
- Corporation Assets
- Character Assets
- Location Overview
- System Name, Solar System Name Handler

### Changed

- Updated dependencies
  - `allianceauth-app-utils` to `>=2b2`
  - `django-esi` to `8,<9`
- Assets System
- Refactor Modal System
- Handle Button HTML in Python
- Fetch Menu Request Count from API
- Task Update Interval

### Removed

- csrf arg from `django-ninja`
- allow-direct-references

## [0.1.2] - 2024-09-23

### Fixed

- PyPi Pakage was wrong

## [0.1.1] - 2024-09-11

### Added

- Canceled Requests disappear after 3 days.
- Request Information at Conformation Modal

### Fixed

- DJANGO Static error
- Translation not showing correctly

## [0.1.0] - 2024-08-28

### Added

- Initial public release

<!-- Links -->

[0.1.1]: https://github.com/Geuthur/aa-assets/compare/v0.1.0...v0.1.1 "0.1.1"
[0.1.2]: https://github.com/Geuthur/aa-assets/compare/v0.1.1...v0.1.2 "0.1.2"
[0.2.0]: https://github.com/Geuthur/aa-assets/compare/v0.1.2...v0.2.0 "0.2.0"
[in development]: https://github.com/Geuthur/aa-assets/compare/v1.0.0...HEAD "In Development"
