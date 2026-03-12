# Changelog

## [In Development] - Unreleased

<!--
Section Order:

### Added
### Fixed
### Changed
### Removed
-->

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
