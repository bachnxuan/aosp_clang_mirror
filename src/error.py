class GitilesError(RuntimeError):
    """Base exception for all Gitiles operations."""


class GitilesHTTPError(GitilesError):
    """Raised when the Gitiles server returns an HTTP error."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class GitilesFormatError(GitilesError):
    """Raised when a Gitiles response cannot be parsed or validated."""


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing or invalid."""


class TelegramError(RuntimeError):
    """Raised when sending a Telegram notification fails."""
