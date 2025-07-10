"""AA Hooks"""

import logging

from allianceauth.authentication.models import UserProfile

from assets.app_settings import ASSETS_APP_NAME


def get_extension_logger(name):
    """
    Takes the name of a plugin/extension and generates a child logger of the extensions logger
    to be used by the extension to log events to the extensions logger.

    The logging level is determined by the level defined for the parent logger.

    :param: name: the name of the extension doing the logging
    :return: an extensions child logger
    """

    logger_name = "assets" if ASSETS_APP_NAME else "extensions"

    if not isinstance(name, str):
        raise TypeError(
            f"get_extension_logger takes an argument of type string."
            f"Instead received argument of type {type(name).__name__}."
        )

    parent_logger = logging.getLogger(logger_name)

    logger = logging.getLogger(logger_name + "." + name)
    logger.name = name
    logger.level = parent_logger.level

    return logger


def add_info_to_context(request, context: dict) -> dict:
    """Add additional information to the context for the view."""
    # pylint: disable=import-outside-toplevel, cyclic-import
    theme = None
    try:
        user = UserProfile.objects.get(id=request.user.id)
        theme = user.theme
    except UserProfile.DoesNotExist:
        pass

    new_context = {
        **{
            "theme": theme,
        },
        **context,
    }
    return new_context
