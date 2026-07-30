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


class CourseNotFoundError(ResourceNotFoundError):
    code = "course_not_found"

    def __init__(self) -> None:
        super().__init__("The requested course does not exist.")


class CourseSourceNotFoundError(ResourceNotFoundError):
    code = "course_source_not_found"

    def __init__(self) -> None:
        super().__init__("The requested course material does not exist.")


class NoteNotFoundError(ResourceNotFoundError):
    code = "note_not_found"

    def __init__(self) -> None:
        super().__init__("The requested course note does not exist.")


class InvalidNoteSlideReferenceError(ApplicationError):
    code = "invalid_note_slide_reference"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CourseSourceFileTooLargeError(ApplicationError):
    code = "course_source_file_too_large"
    status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    def __init__(self, maximum_mb: int) -> None:
        super().__init__(f"The course file exceeds the {maximum_mb} MB upload limit.")


class InvalidCourseSourceFileError(ApplicationError):
    code = "invalid_course_source_file"

    def __init__(self, message: str = "The uploaded course file is not valid.") -> None:
        super().__init__(message)


class CourseSourceStorageError(ApplicationError):
    code = "course_source_storage_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str = "Course file storage is temporarily unavailable.") -> None:
        super().__init__(message)


class CourseSourceExtractionStateError(ApplicationError):
    code = "course_source_extraction_state"
    status_code = HTTPStatus.CONFLICT

    def __init__(self, message: str) -> None:
        super().__init__(message)


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


class AssistantConversationNotFoundError(ResourceNotFoundError):
    code = "assistant_conversation_not_found"

    def __init__(self) -> None:
        super().__init__("The requested assistant conversation does not exist.")


class AssistantJobNotFoundError(ResourceNotFoundError):
    code = "assistant_job_not_found"

    def __init__(self) -> None:
        super().__init__("The requested assistant job does not exist.")


class AssistantRuntimeError(ApplicationError):
    code = "assistant_unavailable"
    status_code = HTTPStatus.SERVICE_UNAVAILABLE

    def __init__(
        self,
        message: str = "The calendar assistant is temporarily unavailable. Try again safely.",
    ) -> None:
        super().__init__(message)


class AssistantNotConfiguredError(AssistantRuntimeError):
    code = "assistant_not_configured"

    def __init__(self) -> None:
        super().__init__(
            "The calendar assistant is not connected. Sign in with ChatGPT on the "
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

    def __init__(self) -> None:
        super().__init__("The assistant returned an invalid response. No calendar data changed.")


class AssistantProposalLimitError(AssistantRuntimeError):
    code = "assistant_proposal_limit"

    def __init__(self) -> None:
        super().__init__(
            "Each executable proposal may affect at most 10 events. Split independent "
            "event creations into linked batches and keep every batch at 10 or fewer."
        )


class AssistantJobNotRetryableError(ApplicationError):
    code = "assistant_job_not_retryable"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("Only a failed assistant job can be retried.")


class AssistantProposalNotFoundError(ResourceNotFoundError):
    code = "assistant_proposal_not_found"

    def __init__(self) -> None:
        super().__init__("The requested assistant proposal does not exist.")


class AssistantProposalStateError(ApplicationError):
    code = "assistant_proposal_state_conflict"
    status_code = HTTPStatus.CONFLICT

    def __init__(self, message: str = "This proposal can no longer be changed.") -> None:
        super().__init__(message)
