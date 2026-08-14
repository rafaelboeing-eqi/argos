class BrapiError(Exception):
    """Base error for any failure talking to the brapi API."""


class BrapiNotConfiguredError(BrapiError):
    """Raised when BRAPI_API_TOKEN is missing."""


class BrapiAuthenticationError(BrapiError):
    """HTTP 401 - invalid or missing token."""


class BrapiPermissionError(BrapiError):
    """HTTP 403 - token valid but without access to the resource."""


class BrapiTimeoutError(BrapiError):
    """The request to brapi timed out."""


class BrapiRequestError(BrapiError):
    """Any other non-2xx response or transport failure."""


class BrapiInvalidResponseError(BrapiError):
    """The response was 2xx but did not contain the expected shape."""
