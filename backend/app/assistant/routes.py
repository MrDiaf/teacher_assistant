import uuid
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.service import AiModelRegistry
from app.assistant.proposal_service import ProposalService
from app.assistant.schemas import (
    AssistantAuthStatusResponse,
    AssistantDeviceLoginResponse,
    AssistantJobResponse,
    AssistantMessageCreate,
    AssistantMessageResponse,
    AssistantProposalResponse,
    AssistantTurnResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
)
from app.assistant.service import AssistantService, AssistantTurn
from app.codex_runtime.adapter import (
    CodexAdapter,
    CodexAuth,
    CodexDeviceLoginAttempt,
    get_codex_adapter,
    get_codex_auth_manager,
)
from app.database.session import get_session

router = APIRouter()
SessionDependency = Annotated[AsyncSession, Depends(get_session)]
AdapterDependency = Annotated[CodexAdapter, Depends(get_codex_adapter)]
AuthDependency = Annotated[CodexAuth, Depends(get_codex_auth_manager)]


def device_login_response(attempt: CodexDeviceLoginAttempt) -> AssistantDeviceLoginResponse:
    return AssistantDeviceLoginResponse(
        login_id=attempt.login_id,
        verification_url=attempt.verification_url,
        user_code=attempt.user_code,
        status=attempt.status,
        safe_error=attempt.safe_error,
    )


def turn_response(turn: AssistantTurn) -> AssistantTurnResponse:
    return AssistantTurnResponse(
        conversation=ConversationResponse.model_validate(turn.conversation),
        owner_message=AssistantMessageResponse.model_validate(turn.owner_message),
        assistant_message=(
            AssistantMessageResponse.model_validate(turn.assistant_message)
            if turn.assistant_message is not None
            else None
        ),
        job=AssistantJobResponse.model_validate(turn.job),
        proposal=(
            AssistantProposalResponse.model_validate(turn.proposal)
            if turn.proposal is not None
            else None
        ),
        proposals=[
            AssistantProposalResponse.model_validate(proposal)
            for proposal in turn.proposals
        ],
    )


@router.get("/assistant/auth", response_model=AssistantAuthStatusResponse)
async def get_assistant_auth(auth: AuthDependency) -> AssistantAuthStatusResponse:
    return AssistantAuthStatusResponse.model_validate(
        await auth.account_status(), from_attributes=True
    )


@router.post(
    "/assistant/auth/device-code",
    response_model=AssistantDeviceLoginResponse,
    status_code=HTTPStatus.CREATED,
)
async def start_assistant_device_login(auth: AuthDependency) -> AssistantDeviceLoginResponse:
    return device_login_response(await auth.start_device_login())


@router.get(
    "/assistant/auth/device-code/{login_id}",
    response_model=AssistantDeviceLoginResponse,
)
async def get_assistant_device_login(
    login_id: str,
    auth: AuthDependency,
) -> AssistantDeviceLoginResponse:
    return device_login_response(await auth.get_device_login(login_id))


@router.delete("/assistant/auth", response_model=AssistantAuthStatusResponse)
async def logout_assistant(auth: AuthDependency) -> AssistantAuthStatusResponse:
    return AssistantAuthStatusResponse.model_validate(await auth.logout(), from_attributes=True)


@router.get("/assistant/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    session: SessionDependency,
    adapter: AdapterDependency,
) -> list[ConversationResponse]:
    conversations = await AssistantService(session, adapter).list_conversations()
    return [ConversationResponse.model_validate(item) for item in conversations]


@router.post(
    "/assistant/conversations",
    response_model=ConversationResponse,
    status_code=HTTPStatus.CREATED,
)
async def create_conversation(
    payload: ConversationCreate,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> ConversationResponse:
    conversation = await AssistantService(session, adapter).create_conversation(payload.title)
    return ConversationResponse.model_validate(conversation)


@router.get(
    "/assistant/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation(
    conversation_id: uuid.UUID,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> ConversationDetailResponse:
    detail = await AssistantService(session, adapter).get_conversation(conversation_id)
    return ConversationDetailResponse(
        **ConversationResponse.model_validate(detail.conversation).model_dump(),
        messages=[AssistantMessageResponse.model_validate(item) for item in detail.messages],
        jobs=[AssistantJobResponse.model_validate(item) for item in detail.jobs],
        proposals=[AssistantProposalResponse.model_validate(item) for item in detail.proposals],
    )


@router.post(
    "/assistant/conversations/{conversation_id}/messages",
    response_model=AssistantTurnResponse,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: AssistantMessageCreate,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> AssistantTurnResponse:
    turn = await AssistantService(session, adapter).send_message(
        conversation_id,
        payload.content,
        payload.model,
    )
    return turn_response(turn)


@router.get("/assistant/jobs/{job_id}", response_model=AssistantJobResponse)
async def get_job(
    job_id: uuid.UUID,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> AssistantJobResponse:
    job = await AssistantService(session, adapter).get_job(job_id)
    return AssistantJobResponse.model_validate(job)


@router.post("/assistant/jobs/{job_id}/retry", response_model=AssistantTurnResponse)
async def retry_job(
    job_id: uuid.UUID,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> AssistantTurnResponse:
    turn = await AssistantService(session, adapter).retry_job(job_id)
    return turn_response(turn)


@router.get(
    "/assistant/audit",
    response_model=list[AssistantProposalResponse],
)
async def list_assistant_audit(
    session: SessionDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[AssistantProposalResponse]:
    proposals = await ProposalService(session).list_audit(limit=limit)
    return [AssistantProposalResponse.model_validate(item) for item in proposals]


@router.get(
    "/assistant/proposals/{proposal_id}",
    response_model=AssistantProposalResponse,
)
async def get_proposal(
    proposal_id: uuid.UUID,
    session: SessionDependency,
) -> AssistantProposalResponse:
    proposal = await ProposalService(session).get(proposal_id)
    return AssistantProposalResponse.model_validate(proposal)


@router.post(
    "/assistant/proposals/{proposal_id}/confirm",
    response_model=AssistantProposalResponse,
)
async def confirm_proposal(
    proposal_id: uuid.UUID,
    session: SessionDependency,
) -> AssistantProposalResponse:
    proposal = await ProposalService(session).confirm(proposal_id)
    return AssistantProposalResponse.model_validate(proposal)


@router.post(
    "/assistant/proposals/{proposal_id}/reject",
    response_model=AssistantProposalResponse,
)
async def reject_proposal(
    proposal_id: uuid.UUID,
    session: SessionDependency,
) -> AssistantProposalResponse:
    proposal = await ProposalService(session).reject(proposal_id)
    return AssistantProposalResponse.model_validate(proposal)


@router.post(
    "/assistant/proposals/{proposal_id}/revise",
    response_model=AssistantTurnResponse,
)
async def revise_proposal(
    proposal_id: uuid.UUID,
    payload: AssistantMessageCreate,
    session: SessionDependency,
    adapter: AdapterDependency,
) -> AssistantTurnResponse:
    selected_model = AiModelRegistry().resolve(payload.model)
    proposal = await ProposalService(session).reject_plan(proposal_id)
    turn = await AssistantService(session, adapter).send_message(
        proposal.conversation_id,
        payload.content,
        selected_model,
    )
    return turn_response(turn)
