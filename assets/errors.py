"""Custom exceptions."""

# Alliance Auth
from esi.errors import TokenError


class TokenDoesNotExist(TokenError):
    """A token with a specific scope does not exist for a user."""


class DatabaseError(Exception):
    pass


class CustomError(Exception):
    pass


class ObjectNotFound(Exception):
    """Custom exception to indicate that an object was not found."""


class DownTimeError(Exception):
    """Custom exception to indicate ESI is in daily downtime."""
