"""Documents-owned application and storage errors."""

from http import HTTPStatus

from app.core.errors import ApplicationError, ResourceNotFoundError


class DocumentProjectNotFoundError(ResourceNotFoundError):
    code = "document_project_not_found"

    def __init__(self) -> None:
        super().__init__("The requested document project does not exist.")


class DocumentTagNotFoundError(ResourceNotFoundError):
    code = "document_tag_not_found"

    def __init__(self) -> None:
        super().__init__("The requested document tag does not exist.")


class DocumentTagConflictError(ApplicationError):
    code = "document_tag_conflict"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("A document tag with that name already exists.")


class DocumentStorageError(ApplicationError):
    code = "document_storage_error"
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(self, message: str = "Private document storage is unavailable.") -> None:
        super().__init__(message)


class DocumentStorageMismatchError(ApplicationError):
    code = "document_storage_mismatch"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__(
            "The document metadata and private source storage do not match. "
            "Restore a coordinated backup before changing this project."
        )
