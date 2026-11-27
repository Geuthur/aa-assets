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

## [0.3.0] - 2026-11-28

> [!IMPORTANT]
> Basic access is only granted by `basic_access`. Users with higher permissions (`corporation_access`, `manage_requests`, `manage_corporation`, `admin_access`) but without `basic_access` lose access to the API and to the pages to add a corporation and to complete or reopen requests. Grant `basic_access` to these users or groups.

### Added

- User settings with the option to disable notifications, readable and editable through the API (`settings/`)
- API endpoints to create orders and to cancel, complete or reopen them, plus `menu/`, `user/`, `owners/` (update status), `requests/{id}/` and `admin/tasks/` for the coming React frontend
- React frontend for locations, assets with single and multi order, requests, administration and settings, with the update status of every owner
- The location page prefills the location flag filter from `?flag=<flag>` (e.g. `/assets/location/<id>/?flag=CorpSAG5`)
- Python 3.13 Support
- Compatibility to Alliance Auth v5

### Fixed

- `?flag=<flag>` on the location page now filters: assets of `location/{location_id}/flag/{location_flag}/` carry the flag code as `location_flag_code`, the table matches it and shows its label in the filter
- `requests/{id}/`, its `cancel/`, `complete/` and `reopen/` and `owners/{id}/` answer an order or owner of someone else with 404 like a missing one (before 403 or 409), so they no longer reveal which IDs exist or the requestor's name
- React Query no longer retries 403, 404 and other 4xx answers three times, so the error shows at once instead of after about seven seconds: `Routing.tsx` uses `createQueryClient` of `aa-geuthur-react` (`^1.7.0`), which retries only network errors and 502/503/504
- Users only see and order assets they may see: `location/`, `location/{location_id}/flag/{location_flag}/`, `requests/order/{request_id}/`, the multi order form of the assets page and the `create_order` view no longer show or accept assets, locations and orders of other owners and users
- Users without corporation or admin access see the assets of their own characters again (`View Assets` answered 403)
- Orders can no longer exceed the available quantity of an asset when it has no other open orders
- An empty asset list from ESI now removes the old assets of the owner instead of keeping them
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
- Fixed `make coverage` exiting with 0 when tests failed. The reports are still created, and the target now exits with the status of the test run, or with the status of `coverage report` if the tests passed.

### Changed

- Location page: assets go into an order cart ("Add", whole quantity), a floating bar opens the review with amounts per asset and places one order; the "Multi Order" button is gone
- The app opens the React frontend; the old Django pages are removed
- The menu badge of open requests pulses (`has_errors` in `menu/`); `price` of an asset is `null` instead of `"N/A"` without a price
- Uniform error format of the API: every error response is an `ErrorSchema` (`{"error": "<text>"}`) instead of a plain string, and every endpoint lists its 403 in the OpenAPI schema; status codes are unchanged, the order modal shows the message of the API
- Every URL of the API requires `basic_access` (403 otherwise). `add_corp`, `mark_request_completed` and `mark_request_open` require it in addition to their own permission, and `add_corp` and `add_char` check the permissions before the SSO step
- Permissions are checked only through `GeneralManager` (new `has_basic_access`, `has_corporation_access`, `has_manage_requests_access`, `has_admin_access` next to `has_management_access`), `General.Meta.permissions` is the single place that defines them (texts now translatable, no migration); unreachable `basic_access` and `is None` checks in the API are removed. No change in behavior
- The access rules of assets, locations, owners and requests share `AccessQuerySet` and `AccessManager` in `managers/general.py`; `models.py` and `managers.py` are split into the packages `assets/models/` and `assets/managers/` (imports keep working, no migration)
- The asset update of an owner runs through the `UpdateManager` of the app template: `OwnerUpdateStatus` keeps success, errors and token errors per owner and section, replacing `Owner.last_update` (migration `0004_owner_update_status`). New setting `ASSETS_STALE_TYPES` (default: `ASSETS_UPDATE_PERIOD`)
- `retry_task_on_esi_error` follows the app template: ESI outages retry after `DOWNTIME_TIMER` (10 minutes), the daily downtime (11:00-11:15 UTC) is checked (can be disabled with `DISABLE_DAILY_DOWNTIME_CHECK`), new `is_retryable_esi_error` and `DownTimeError`
- Stations are read from the SDE (`eve_sde` `NPCStation`) instead of the ESI route `/universe/stations/{station_id}`, which CCP removes with compatibility date `2026-11-19`; only the station name still comes from ESI (`PostUniverseNames`)
- ESI client loads the OpenAPI spec from a bundled file (`assets/openapi_2026-08-18.json`), compatibility date raised from `2026-07-21` to `2026-08-18`, and the ESI operations are merged into a single `__operations__` list (same set of operations)
- `get_location_type` returns `None` explicitly in all branches instead of the always-`None` `existing_location` or a QuerySet, matching its type hint; no change in behavior
- The `AppLogger` is created only once in `assets/providers.py` and imported everywhere; all log records go to the `extensions.assets` logger described in the README
- `.make/config.ini` names aa-assets instead of the app template, and `helpers/eveonline.py` matches the template (new `display_name` option)
- Dropped Python 3.10 (end of life): `requires-python` is now `>=3.11`
- i18next 27, react-i18next 18 (aa-geuthur-react `^1.8.0`) and stylelint 18. A plural form left empty in a language (e.g. `_few` in pl, ru, uk) now shows that language's `_other` form instead of English
- Development: Node 26 in CI and pre-commit, npm updates in the root and `frontend/`, ESLint enforces the import order, CI workflows aligned with the aa-example template, `.isort.cfg` moved to the repository root
- Tests: users and characters from `UserMainFactory` and `add_character_to_user` of `aa-evesde-factory`, base class `AuthTestCase` like in the other apps, `pookx` instead of `pook`, ESI tests against pook responses under the real ESI URL (own ESI stub removed), new tests for permissions, `is_retryable_esi_error` and the image helpers, downtime tests independent of the time of day

### Removed

- Unused endpoint `requests/statistics/` with its manager methods `my_requests_open` and `my_requests_total_count`, and the empty `templatetags` module
- Unused and broken `manage_to` of `Assets`, `Location` and `Request` querysets, plus the copies of `visible_eve_characters` and `manage_eve_characters` in the `Request` manager; `Owner.objects.visible_eve_characters` stays the only one
- The old Django pages (locations, assets, requests), their order and status views, templates, jQuery/DataTables scripts and `forms.py`, plus the HTML fields `order`/`actions` of `requests/`, the field `view` of `location/` and the endpoint `requests/order/{id}/`
- Unused `assets/decorators.py` (`log_timing` and two unused constants) and its test
- Unused `HTTPGatewayTimeoutError` (`assets/errors.py`) and its dead `except` branch in `Owner.update_assets_esi`
- Own HTTP 420 retry in `update_location` and `update_parent_location`: django-esi raises `ESIErrorLimitException` for HTTP 420, so this code path was never reached
- Compatibility to Alliance Auth v4
- Dependency `allianceauth-app-utils`

> [!WARNING]
>
> Please note that this release involves structural dependency changes.
> To avoid any service disruptions, it is essential to read the update manual prior to performing the upgrade.

### Update Instructions

After installing this version, you need to modify `INSTALLED_APPS` in your `local.py`

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
> This is only for installed Assets environment
> You need to have eveuniverse installed during the migration otherwise it will not migrate the old entries.

After running migrations, make sure to run the following commands to import the SDE data into your database.

```shell
python manage.py esde_load_sde
```

Restart your Auth via `supervisor` after running these commands
