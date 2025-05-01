# Assets module for AllianceAuth.<a name="aa-assets"></a>

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/Geuthur/aa-assets/master.svg)](https://results.pre-commit.ci/latest/github/Geuthur/aa-assets/master)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests](https://github.com/Geuthur/aa-assets/actions/workflows/autotester.yml/badge.svg)](https://github.com/Geuthur/aa-assets/actions/workflows/autotester.yml)
[![codecov](https://codecov.io/gh/Geuthur/aa-assets/graph/badge.svg?token=JumsRpUngc)](https://codecov.io/gh/Geuthur/aa-assets)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/W7W810Q5J4)

Assets System with Ordering Feature

## -

- [AA Assets](#aa-assets)
  - [Features](#features)
  - [Upcoming](#upcoming)
  - [Installation](#features)
    - [Step 1 - Install the Package](#step1)
    - [Step 2 - Configure Alliance Auth](#step2)
    - [Step 3 - Add the Scheduled Tasks and Settings](#step3)
    - [Step 4 - Migration to AA](#step4)
    - [Step 5 - Setting up Permissions](#step5)
    - [Step 6 - (Optional) Setting up Compatibilies](#step6)
  - [Highlights](#highlights)

## Features<a name="features"></a>

- Asset System for Character & Corporation
- Ordering System

## Upcoming<a name="upcoming"></a>

- Performance Updates
- More Filter
- Notifications
- Status Updates

## Installation<a name="installation"></a>

> [!NOTE]
> AA Assets needs at least Alliance Auth v4.0.0
> Please make sure to update your Alliance Auth before you install this APP

### Step 1 - Install the Package<a name="step1"></a>

Make sure you're in your virtual environment (venv) of your Alliance Auth then install the pakage.

```shell
pip install aa-assets
```

### Step 2 - Configure Alliance Auth<a name="step2"></a>

Configure your Alliance Auth settings (`local.py`) as follows:

- Add `'eveuniverse',` to `INSTALLED_APPS`
- Add `'assets',` to `INSTALLED_APPS`

### Step 3 - Add the Scheduled Tasks<a name="step3"></a>

To set up the Scheduled Tasks add following code to your `local.py`

```python
CELERYBEAT_SCHEDULE["assets_update_all_assets"] = {
    "task": "assets.tasks.update_all_assets",
    "schedule": crontab(minute="*/15"),
}
CELERYBEAT_SCHEDULE["assets_update_all_locations"] = {
    "task": "assets.tasks.update_all_locations",
    "schedule": crontab(minute=0, hour="*/12"),
}
CELERYBEAT_SCHEDULE["assets_update_all_parent_locations"] = {
    "task": "assets.tasks.update_all_parent_locations",
    "schedule": crontab(minute=0, hour=0, day_of_week=0),
}
```

### Step 4 - Migration to AA<a name="step4"></a>

```shell
python manage.py collectstatic
python manage.py migrate
```

### Step 5 - Setting up Permissions<a name="step5"></a>

With the Following IDs you can set up the permissions for the Assets

| ID                    | Description                  |                                                        |
| :-------------------- | :--------------------------- | :----------------------------------------------------- |
| `basic_access`        | Can access the Assets module | All Members with the Permission can access the Assets. |
| `add_personal_owner`  | Can add personal owners      |                                                        |
| `add_corporate_owner` | Can add corporate owners     |                                                        |
| `manage_requests`     | Can manage requests          | Get Notifications & Manage Requests                    |

### Step 6 - (Optional) Setting up Compatibilies<a name="step6"></a>

The Following Settings can be setting up in the `local.py`

- ASSETS_APP_NAME: `"YOURNAME"` - Set the name of the APP

- ASSETS_LOGGER_USE: `True / False` - Set to use own Logger File

If you set up ASSETS_LOGGER_USE to `True` you need to add the following code below:

```python
LOGGING_ASSETS = {
    "handlers": {
        "assets_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "log/assets.log"),
            "formatter": "verbose",
            "maxBytes": 1024 * 1024 * 5,
            "backupCount": 5,
        },
    },
    "loggers": {
        "assets": {
            "handlers": ["assets_file", "console"],
            "level": "INFO",
        },
    },
}
LOGGING["handlers"].update(LOGGING_ASSETS["handlers"])
LOGGING["loggers"].update(LOGGING_ASSETS["loggers"])
```

## Highlights<a name="highlights"></a>

> [!NOTE]
> Contributing
> You want to improve the project?
> Just Make a [Pull Request](https://github.com/Geuthur/aa-assets/pulls) with the Guidelines.
> We Using pre-commit
