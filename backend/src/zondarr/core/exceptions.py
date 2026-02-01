"""Domain exceptions for Zondarr.

All domain exceptions inherit from ZondarrError base class.
"""


class ZondarrError(Exception):
    """Base exception for all Zondarr errors."""

    message: str
    error_code: str
    context: dict[str, str | int | bool | None]

    def __init__(
        self, message: str, error_code: str, **context: str | int | bool | None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context


class ConfigurationError(ZondarrError):
    """Raised when configuration is invalid or missing."""

    pass


class RepositoryError(ZondarrError):
    """Raised when a repository operation fails."""

    original: Exception | None

    def __init__(
        self, message: str, operation: str, original: Exception | None = None
    ) -> None:
        super().__init__(message, "REPOSITORY_ERROR", operation=operation)
        self.original = original


class ValidationError(ZondarrError):
    """Raised when input validation fails."""

    field_errors: dict[str, list[str]]

    def __init__(self, message: str, field_errors: dict[str, list[str]]) -> None:
        super().__init__(message, "VALIDATION_ERROR")
        self.field_errors = field_errors


class NotFoundError(ZondarrError):
    """Raised when a requested resource is not found."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(
            f"{resource_type} not found: {identifier}",
            "NOT_FOUND",
            resource_type=resource_type,
            identifier=identifier,
        )
