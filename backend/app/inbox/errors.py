"""Inbox-owned safe application errors."""

from http import HTTPStatus

from app.core.errors import ApplicationError, ResourceNotFoundError


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
