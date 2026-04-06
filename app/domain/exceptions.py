"""Domain-level exceptions."""


class DomainException(Exception):
    """Base domain exception."""

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class DuplicateRequestError(DomainException):
    """Exception raised when attempting to create a duplicate request."""

    def __init__(self, request_id: str, message: str | None = None):
        self.request_id = request_id
        message = message or f"Request with ID {request_id} already exists"
        super().__init__(message=message, code="DUPLICATE_REQUEST")


class RequestNotFoundError(DomainException):
    """Exception raised when a request is not found."""

    def __init__(self, request_id: str, message: str | None = None):
        self.request_id = request_id
        message = message or f"Request with ID {request_id} not found"
        super().__init__(message=message, code="REQUEST_NOT_FOUND")


# ── Graphics exceptions ──


class GraphicsValidationError(DomainException):
    """Invalid graphics request (unknown product, entity, metric, visualization)."""

    UNKNOWN_PRODUCT = "UNKNOWN_PRODUCT"
    UNKNOWN_ENTITY = "UNKNOWN_ENTITY"
    UNKNOWN_METRIC = "UNKNOWN_METRIC"
    UNSUPPORTED_VISUALIZATION = "UNSUPPORTED_VISUALIZATION"

    def __init__(self, message: str, code: str = "GRAPHICS_VALIDATION_ERROR"):
        super().__init__(message=message, code=code)


class GraphicsPermissionError(DomainException):
    """Access denied for graphics operation."""

    ACCESS_DENIED = "ACCESS_DENIED"
    PROJECT_NOT_AVAILABLE = "PROJECT_NOT_AVAILABLE"

    def __init__(self, message: str, code: str = "ACCESS_DENIED"):
        super().__init__(message=message, code=code)


class GraphicsConfigError(DomainException):
    """Project configuration error."""

    def __init__(self, message: str, code: str = "PROJECT_CONFIG_NOT_FOUND"):
        super().__init__(message=message, code=code)


class GraphicsDataError(DomainException):
    """Data source error (upstream timeout, unavailable)."""

    UPSTREAM_TIMEOUT = "UPSTREAM_TIMEOUT"
    DATA_SOURCE_UNAVAILABLE = "DATA_SOURCE_UNAVAILABLE"

    def __init__(self, message: str, code: str = "DATA_SOURCE_ERROR"):
        super().__init__(message=message, code=code)
