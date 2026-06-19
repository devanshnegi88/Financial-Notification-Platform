from typing import Any, Optional


class FNPBaseException(Exception):
    def __init__(self, message: str, details: Optional[Any] = None):
        self.message = message
        self.details = details
        super().__init__(message)


class NotFoundError(FNPBaseException):
    pass


class ConflictError(FNPBaseException):
    pass


class ValidationError(FNPBaseException):
    pass


class AuthenticationError(FNPBaseException):
    pass


class AuthorizationError(FNPBaseException):
    pass


class ChannelError(FNPBaseException):
    pass


class TemplateRenderError(FNPBaseException):
    pass


class KafkaPublishError(FNPBaseException):
    pass


class RateLimitExceeded(FNPBaseException):
    pass


class FrequencyCapExceeded(FNPBaseException):
    pass


class DNDRegisteredError(FNPBaseException):
    pass


class QuietHoursError(FNPBaseException):
    pass


class RetryExhaustedError(FNPBaseException):
    pass


class InvalidContactError(FNPBaseException):
    pass


class ConfigurationError(FNPBaseException):
    pass
