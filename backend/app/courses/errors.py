"""Courses-owned safe application errors."""

from http import HTTPStatus

from app.core.errors import ApplicationError, AssistantRuntimeError, ResourceNotFoundError


class CourseNotFoundError(ResourceNotFoundError):
    code = "course_not_found"

    def __init__(self) -> None:
        super().__init__("The requested course does not exist.")


class CourseCalendarNotLinkedError(ResourceNotFoundError):
    code = "course_calendar_not_linked"

    def __init__(self) -> None:
        super().__init__("The requested calendar is not linked to this course.")


class CourseSourceNotFoundError(ResourceNotFoundError):
    code = "course_source_not_found"

    def __init__(self) -> None:
        super().__init__("The requested course material does not exist.")


class NoteNotFoundError(ResourceNotFoundError):
    code = "note_not_found"

    def __init__(self) -> None:
        super().__init__("The requested course note does not exist.")


class NoteSummaryNotFoundError(ResourceNotFoundError):
    code = "note_summary_not_found"

    def __init__(self) -> None:
        super().__init__("The requested note summary does not exist.")


class NoteSummaryNotRetryableError(ApplicationError):
    code = "note_summary_not_retryable"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("Only a failed note summary can be retried.")


class NoteSummaryNotEditableError(ApplicationError):
    code = "note_summary_not_editable"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("Bullets can only be removed from a completed note summary.")


class NoteSummaryBulletNotFoundError(ApplicationError):
    code = "note_summary_bullet_not_found"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__(
            "That summary bullet no longer exists. Refresh the note before trying again."
        )


class NoteSummarySourceUnavailableError(ApplicationError):
    code = "note_summary_source_unavailable"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidNoteSlideReferenceError(ApplicationError):
    code = "invalid_note_slide_reference"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CourseSourceFileTooLargeError(ApplicationError):
    code = "course_source_file_too_large"
    status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    def __init__(self, maximum_mb: int) -> None:
        super().__init__(
            f"The course file exceeds the {maximum_mb} MB upload limit.",
            {"maximum_size_mb": maximum_mb},
        )


class InvalidCourseSourceFileError(ApplicationError):
    code = "invalid_course_source_file"

    def __init__(self, message: str = "The uploaded course file is not valid.") -> None:
        super().__init__(message)


class CourseSourceStorageError(ApplicationError):
    code = "course_source_storage_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str = "Course file storage is temporarily unavailable.") -> None:
        super().__init__(message)


class CourseSourceNotPdfError(ApplicationError):
    code = "course_source_not_pdf"
    status_code = HTTPStatus.UNSUPPORTED_MEDIA_TYPE

    def __init__(self) -> None:
        super().__init__("Only uploaded PDF course materials can be opened in the PDF viewer.")


class CourseSourceContentUnavailableError(ApplicationError):
    code = "course_source_content_unavailable"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__(
            "The stored PDF is missing, unreadable, or no longer matches its source record. "
            "Delete this material and upload the PDF again."
        )


class CourseSourceExtractionStateError(ApplicationError):
    code = "course_source_extraction_state"
    status_code = HTTPStatus.CONFLICT

    def __init__(self, message: str) -> None:
        super().__init__(message)


class InvalidNoteSummaryResponseError(AssistantRuntimeError):
    code = "invalid_note_summary_response"

    def __init__(self) -> None:
        super().__init__("The summary response was invalid, so no summary was saved. Retry safely.")


class NotePrettifyInputTooLargeError(ApplicationError):
    code = "note_prettify_input_too_large"
    status_code = HTTPStatus.REQUEST_ENTITY_TOO_LARGE

    def __init__(self, maximum_characters: int) -> None:
        super().__init__(
            f"Prettify accepts up to {maximum_characters:,} characters at a time. "
            "Shorten the draft and try again; the note was not changed."
        )


class InvalidNotePrettifyResponseError(AssistantRuntimeError):
    code = "invalid_note_prettify_response"

    def __init__(self) -> None:
        super().__init__(
            "The prettify suggestion did not preserve the note's required Markdown "
            "and protected content, so it was rejected. The note was not changed."
        )
