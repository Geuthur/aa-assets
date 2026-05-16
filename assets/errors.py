"""Custom exceptions."""


class HTTPGatewayTimeoutError(Exception):
    pass


class DownTimeError(Exception):
    """Custom exception to indicate ESI is in daily downtime."""
