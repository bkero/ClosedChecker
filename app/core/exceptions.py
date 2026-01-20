"""Custom exceptions for the application."""

from typing import Optional


class AppException(Exception):
    """Base exception for the application."""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class TakeoutParseError(AppException):
    """Error parsing Google Takeout data."""

    pass


class PlacesAPIError(AppException):
    """Error communicating with Google Places API."""

    pass


class PlacesAPIKeyMissing(AppException):
    """Google Places API key not provided."""

    def __init__(self):
        super().__init__(
            message="Google Places API key is required",
            details="Please provide your API key in the web interface",
        )


class PlacesAPIQuotaExceeded(PlacesAPIError):
    """Google Places API quota exceeded."""

    def __init__(self):
        super().__init__(
            message="Google Places API quota exceeded",
            details="Wait and try again later, or check your API quota",
        )


class PlaywrightError(AppException):
    """Error with Playwright automation."""

    pass


class AuthenticationRequired(PlaywrightError):
    """Google authentication is required."""

    def __init__(self):
        super().__init__(
            message="Google authentication required",
            details="Please complete the authentication flow first",
        )


class AuthenticationExpired(PlaywrightError):
    """Saved authentication has expired."""

    def __init__(self):
        super().__init__(
            message="Authentication has expired",
            details="Please re-authenticate with Google",
        )


class JobNotFoundError(AppException):
    """Requested job ID not found."""

    def __init__(self, job_id: str):
        super().__init__(
            message=f"Job not found: {job_id}",
            details="The job may have expired or never existed",
        )


class InvalidFileError(AppException):
    """Uploaded file is invalid."""

    pass
