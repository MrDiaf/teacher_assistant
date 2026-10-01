"""Assistant-owned conversation, job, and proposal errors."""

from http import HTTPStatus

from app.core.errors import ApplicationError, AssistantRuntimeError, ResourceNotFoundError


class AssistantConversationNotFoundError(ResourceNotFoundError):
    code = "assistant_conversation_not_found"

    def __init__(self) -> None:
        super().__init__("The requested assistant conversation does not exist.")


class AssistantJobNotFoundError(ResourceNotFoundError):
    code = "assistant_job_not_found"

    def __init__(self) -> None:
        super().__init__("The requested assistant job does not exist.")


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


class AssistantJobNotCancellableError(ApplicationError):
    code = "assistant_job_not_cancellable"
    status_code = HTTPStatus.CONFLICT

    def __init__(self) -> None:
        super().__init__("There is no active Assistant request to cancel.")


class AssistantProposalNotFoundError(ResourceNotFoundError):
    code = "assistant_proposal_not_found"

    def __init__(self) -> None:
        super().__init__("The requested assistant proposal does not exist.")


class AssistantProposalStateError(ApplicationError):
    code = "assistant_proposal_state_conflict"
    status_code = HTTPStatus.CONFLICT

    def __init__(self, message: str = "This proposal can no longer be changed.") -> None:
        super().__init__(message)
