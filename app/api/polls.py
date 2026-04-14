from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user_id
from app.db.session import get_db
from app.schemas.poll import (
    PollClosedResponse,
    PollCreateInternal,
    PollCreateRequest,
    PollCreatedResponse,
    PollListResponse,
    PollResultsResponse,
    PollVoteRequest,
    VoteCreatedResponse,
)
from app.services.polls import (
    close_poll,
    create_poll,
    get_results,
    list_polls,
    vote,
)

router = APIRouter(prefix="/polls", tags=["polls"])


@router.post(
    "",
    response_model=PollCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_poll_view(
    payload: PollCreateRequest,
    db: Session = Depends(get_db),
) -> PollCreatedResponse:
    """создает опрос"""

    return create_poll(db, PollCreateInternal.from_request(payload))


@router.get("", response_model=PollListResponse)
def list_polls_view(db: Session = Depends(get_db)) -> PollListResponse:
    """возвращает список опросов"""

    return list_polls(db)


@router.post(
    "/{poll_id}/votes",
    response_model=VoteCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def vote_view(
    poll_id: UUID,
    payload: PollVoteRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> VoteCreatedResponse:
    """сохраняет голос"""

    return vote(
        db,
        poll_id=poll_id,
        option_id=payload.option_id,
        user_id=current_user_id,
    )


@router.get("/{poll_id}/results", response_model=PollResultsResponse)
def poll_results_view(
    poll_id: UUID,
    db: Session = Depends(get_db),
) -> PollResultsResponse:
    """возвращает результаты опроса"""

    return get_results(db, poll_id=poll_id)


@router.post("/{poll_id}/close", response_model=PollClosedResponse)
def close_poll_view(
    poll_id: UUID,
    db: Session = Depends(get_db),
) -> PollClosedResponse:
    """закрывает опрос"""

    return close_poll(db, poll_id=poll_id)
