class JobHunterError(Exception):
    """Base exception."""


class LoginError(JobHunterError):
    pass


class CaptchaRequired(JobHunterError):
    pass


class ExtractorError(JobHunterError):
    pass


class StopSignal(JobHunterError):
    """Raised when user requests stop via UI."""
