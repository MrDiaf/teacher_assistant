"""Calendar-owned safe application errors."""

from http import HTTPStatus

from app.core.errors import ApplicationError, ResourceNotFoundError


class CalendarNotFoundError(ResourceNotFoundError):
    code = "calendar_not_found"

    def __init__(self) -> None:
        super().__init__("The requested calendar does not exist.")


class EventNotFoundError(ResourceNotFoundError):
    code = "event_not_found"

    def __init__(self) -> None:
        super().__init__("The requested event does not exist.")


class CalendarReadOnlyError(ApplicationError):
    code = "calendar_read_only"
    status_code = HTTPStatus.FORBIDDEN

    def __init__(self) -> None:
        super().__init__("This calendar is read-only and cannot be modified.")


class CalendarSourceProtectedError(ApplicationError):
    code = "calendar_source_protected"
    status_code = HTTPStatus.FORBIDDEN

    def __init__(self) -> None:
        super().__init__("Imported calendars cannot be made writable or deleted.")


class InvalidEventTimeError(ApplicationError):
    code = "invalid_event_time"

    def __init__(self) -> None:
        super().__init__("Event end time must be later than its start time.")


class InvalidRecurrenceParentError(ApplicationError):
    code = "invalid_recurrence_parent"

    def __init__(self) -> None:
        super().__init__("The recurrence parent must exist in the same calendar.")


class InvalidRecurrenceError(ApplicationError):
    code = "invalid_recurrence"

    def __init__(self, message: str = "The recurrence request is not valid.") -> None:
        super().__init__(message)


class InvalidIcsError(ApplicationError):
    code = "invalid_ics"

    def __init__(self, message: str = "The ICS file is malformed or unsupported.") -> None:
        super().__init__(message)


class IcsFileTooLargeError(ApplicationError):
    code = "ics_file_too_large"
    status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    def __init__(self) -> None:
        super().__init__("The ICS file exceeds the 5 MB upload limit.")


class DuplicateExternalUidError(ApplicationError):
    code = "duplicate_external_uid"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("An event with the same external UID already exists in that calendar.")


class InvalidIcsSubscriptionUrlError(ApplicationError):
    code = "invalid_ics_subscription_url"

    def __init__(self, message: str = "Enter a valid public HTTP or HTTPS ICS URL.") -> None:
        super().__init__(message)


class IcsSubscriptionFetchError(ApplicationError):
    code = "ics_subscription_fetch_failed"
    status_code = HTTPStatus.BAD_GATEWAY

    def __init__(self, message: str = "The subscribed calendar could not be downloaded.") -> None:
        super().__init__(message)


class IcsSubscriptionNotFoundError(ResourceNotFoundError):
    code = "ics_subscription_not_found"

    def __init__(self) -> None:
        super().__init__("The requested calendar is not an ICS subscription.")
