from http import HTTPStatus
from typing import Any


class ApplicationError(Exception):
    code = "application_error"
    status_code = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ResourceNotFoundError(ApplicationError):
    code = "resource_not_found"
    status_code = HTTPStatus.NOT_FOUND


class MailConnectionError(ApplicationError):
    code = "mail_connection_error"
    status_code = HTTPStatus.BAD_GATEWAY

    def __init__(
        self, message: str = "The mailbox connection could not be completed safely."
    ) -> None:
        super().__init__(message)


class InvalidMailConnectionError(ApplicationError):
    code = "invalid_mail_connection"


class MailReconnectRequiredError(ApplicationError):
    code = "mail_reconnect_required"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("Reconnect the dedicated mailbox in Settings before checking mail.")


class MailMessageNotFoundError(ResourceNotFoundError):
    code = "mail_message_not_found"

    def __init__(self) -> None:
        super().__init__("The requested Inbox message does not exist.")


class MailAttachmentNotFoundError(ResourceNotFoundError):
    code = "mail_attachment_not_found"

    def __init__(self) -> None:
        super().__init__("The requested mail attachment does not exist.")


class MailAttachmentUnavailableError(ApplicationError):
    code = "mail_attachment_unavailable"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("This attachment is omitted, missing, or failed its storage check.")


class MailStorageError(ApplicationError):
    code = "mail_storage_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str = "Private mail storage is temporarily unavailable.") -> None:
        super().__init__(message)


class InvalidAiModelError(ApplicationError):
    code = "invalid_ai_model"

    def __init__(self, allowed_models: tuple[str, ...]) -> None:
        allowed = ", ".join(allowed_models)
        super().__init__(
            f"That AI model is not allowed by this installation. Choose one of: {allowed}."
        )


class AssistantRuntimeError(ApplicationError):
    code = "assistant_unavailable"
    status_code = HTTPStatus.SERVICE_UNAVAILABLE

    def __init__(
        self,
        message: str = "The private AI runtime is temporarily unavailable. Try again safely.",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)


class AssistantNotConfiguredError(AssistantRuntimeError):
    code = "assistant_not_configured"

    def __init__(self) -> None:
        super().__init__(
            "The private AI runtime is not connected. Sign in with ChatGPT on the "
            "Assistant page, or configure the optional API-key fallback."
        )


class AssistantAuthError(AssistantRuntimeError):
    code = "assistant_auth_unavailable"

    def __init__(self) -> None:
        super().__init__("ChatGPT sign-in is temporarily unavailable. Try again safely.")


class AssistantLoginAttemptNotFoundError(ResourceNotFoundError):
    code = "assistant_login_attempt_not_found"

    def __init__(self) -> None:
        super().__init__("This ChatGPT sign-in attempt is no longer active. Start again.")


class InvalidAssistantResponseError(AssistantRuntimeError):
    code = "invalid_assistant_response"

    def __init__(
        self,
        reason: str = "The reply did not match the required safe response format.",
        *,
        validation_stage: str = "response_validation",
        validation_errors: list[dict[str, str]] | None = None,
    ) -> None:
        details: dict[str, Any] = {
            "reason": reason,
            "validation_stage": validation_stage,
        }
        if validation_errors:
            details["validation_errors"] = validation_errors
        super().__init__(
            "The assistant's reply did not match the required safe response format, "
            "so the backend rejected it before saving an answer or changing calendar data.",
            details,
        )


class InvalidDiagnosticExplanationError(AssistantRuntimeError):
    code = "invalid_diagnostic_explanation"

    def __init__(self) -> None:
        super().__init__(
            "The Assistant returned an invalid error explanation. The application was not changed."
        )


class DiagnosticErrorNotFoundError(ResourceNotFoundError):
    code = "diagnostic_error_not_found"

    def __init__(self) -> None:
        super().__init__("The requested sanitized error report does not exist.")
