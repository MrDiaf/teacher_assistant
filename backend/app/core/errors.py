from http import HTTPStatus


class ApplicationError(Exception):
    code = "application_error"
    status_code = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ResourceNotFoundError(ApplicationError):
    code = "resource_not_found"
    status_code = HTTPStatus.NOT_FOUND


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
