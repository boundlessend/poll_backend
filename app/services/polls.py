from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, insert, literal, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.errors import ConflictError, NotFoundError
from app.models.poll import Poll, PollOption, Vote
from app.schemas.poll import (
    PollClosedResponse,
    PollCreateInternal,
    PollCreatedResponse,
    PollListItemResponse,
    PollListResponse,
    PollOptionResponse,
    PollResultsResponse,
    PollResultOptionResponse,
    VoteCreatedResponse,
)


def get_poll_or_404(db: Session, poll_id: int) -> Poll:
    """возвращает опрос или ошибку 404"""

    poll = db.scalar(
        select(Poll)
        .where(Poll.id == poll_id)
        .options(selectinload(Poll.options))
    )
    if poll is None:
        raise NotFoundError(
            code="poll_not_found",
            message="Опрос не найден",
            details={"poll_id": poll_id},
        )
    return poll


def get_poll_for_update_or_404(db: Session, poll_id: int) -> Poll:
    """возвращает опрос c блокировкой строки или ошибку 404"""

    poll = db.scalar(select(Poll).where(Poll.id == poll_id).with_for_update())
    if poll is None:
        raise NotFoundError(
            code="poll_not_found",
            message="Опрос не найден",
            details={"poll_id": poll_id},
        )
    return poll


def create_poll(
    db: Session, payload: PollCreateInternal
) -> PollCreatedResponse:
    """создает новый опрос"""

    poll = Poll(question=payload.question, closes_at=payload.closes_at)
    poll.options = [PollOption(text=text) for text in payload.options]

    db.add(poll)
    db.commit()
    db.refresh(poll)

    return PollCreatedResponse(
        id=poll.id,
        question=poll.question,
        status=poll.status,
        closes_at=poll.closes_at,
        options=[
            PollOptionResponse.model_validate(option)
            for option in poll.options
        ],
    )


def list_polls(db: Session) -> PollListResponse:
    """возвращает список опросов"""

    options_subquery = (
        select(
            PollOption.poll_id,
            func.count(PollOption.id).label("options_count"),
        )
        .group_by(PollOption.poll_id)
        .subquery()
    )
    votes_subquery = (
        select(Vote.poll_id, func.count(Vote.id).label("total_votes"))
        .group_by(Vote.poll_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Poll.id,
            Poll.question,
            Poll.created_at,
            Poll.closes_at,
            Poll.closed_at,
            func.coalesce(options_subquery.c.options_count, 0).label(
                "options_count"
            ),
            func.coalesce(votes_subquery.c.total_votes, 0).label(
                "total_votes"
            ),
        )
        .outerjoin(options_subquery, options_subquery.c.poll_id == Poll.id)
        .outerjoin(votes_subquery, votes_subquery.c.poll_id == Poll.id)
        .order_by(Poll.id.desc())
    )

    now = _utcnow()
    items = []
    for row in rows:
        status = (
            "closed"
            if row.closed_at is not None
            or (row.closes_at is not None and _to_utc(row.closes_at) <= now)
            else "open"
        )
        items.append(
            PollListItemResponse(
                id=row.id,
                question=row.question,
                status=status,
                options_count=row.options_count,
                total_votes=row.total_votes,
                closes_at=row.closes_at,
                created_at=row.created_at,
            )
        )
    return PollListResponse(items=items)


def vote(
    db: Session, poll_id: int, option_id: int, voter_id: str
) -> VoteCreatedResponse:
    """сохраняет голос за вариант"""

    poll = get_poll_for_update_or_404(db, poll_id)
    current_time = _utcnow()

    if _is_poll_closed(poll, current_time):
        _persist_auto_close_if_needed(db, poll, current_time)
        raise ConflictError(
            code="poll_closed",
            message="Голосование в закрытом опросе запрещено",
            details={"poll_id": poll_id},
        )

    option = db.scalar(
        select(PollOption).where(
            PollOption.id == option_id, PollOption.poll_id == poll_id
        )
    )
    if option is None:
        raise NotFoundError(
            code="option_not_found",
            message="Вариант ответа не найден в этом опросе",
            details={"poll_id": poll_id, "option_id": option_id},
        )

    insert_vote_stmt = (
        insert(Vote)
        .from_select(
            [Vote.poll_id, Vote.option_id, Vote.voter_id],
            select(
                literal(poll_id),
                literal(option_id),
                literal(voter_id),
            ).where(
                select(Poll.id)
                .where(
                    Poll.id == poll_id,
                    Poll.closed_at.is_(None),
                    or_(Poll.closes_at.is_(None), Poll.closes_at > func.now()),
                )
                .exists()
            ),
        )
        .returning(Vote.id)
    )

    try:
        vote_id = db.scalar(insert_vote_stmt)
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            code="duplicate_vote",
            message="Один участник не может голосовать дважды в одном опросе",
            details={"poll_id": poll_id, "voter_id": voter_id},
        ) from None

    if vote_id is None:
        db.rollback()
        poll = get_poll_for_update_or_404(db, poll_id)
        _persist_auto_close_if_needed(db, poll, _utcnow())
        raise ConflictError(
            code="poll_closed",
            message="Голосование в закрытом опросе запрещено",
            details={"poll_id": poll_id},
        )

    db.commit()
    db.refresh(poll)

    return VoteCreatedResponse(
        poll_id=poll_id,
        option_id=option_id,
        voter_id=voter_id,
        status=poll.status,
    )


def get_results(db: Session, poll_id: int) -> PollResultsResponse:
    """возвращает результаты опроса"""

    poll = get_poll_or_404(db, poll_id)

    rows = db.execute(
        select(
            PollOption.id,
            PollOption.text,
            func.count(Vote.id).label("votes_count"),
        )
        .outerjoin(Vote, Vote.option_id == PollOption.id)
        .where(PollOption.poll_id == poll_id)
        .group_by(PollOption.id)
        .order_by(PollOption.id)
    )

    options = [
        PollResultOptionResponse(
            id=row.id, text=row.text, votes_count=row.votes_count
        )
        for row in rows
    ]

    total_votes = sum(option.votes_count for option in options)

    return PollResultsResponse(
        id=poll.id,
        question=poll.question,
        status=poll.status,
        total_votes=total_votes,
        closes_at=poll.closes_at,
        options=options,
    )


def close_poll(db: Session, poll_id: int) -> PollClosedResponse:
    """закрывает опрос вручную"""

    poll = get_poll_for_update_or_404(db, poll_id)
    current_time = _utcnow()

    if _is_poll_closed(poll, current_time):
        _persist_auto_close_if_needed(db, poll, current_time)
        raise ConflictError(
            code="poll_already_closed",
            message="Опрос уже закрыт",
            details={"poll_id": poll_id},
        )

    poll.closed_at = current_time
    db.commit()
    db.refresh(poll)

    return PollClosedResponse(
        id=poll.id,
        status=poll.status,
        closed_at=poll.closed_at,
    )


def _is_poll_closed(poll: Poll, current_time: datetime) -> bool:
    """проверяет, закрыт ли опрос на текущий момент"""

    if poll.closed_at is not None:
        return True
    if poll.closes_at is not None and _to_utc(poll.closes_at) <= current_time:
        return True
    return False


def _persist_auto_close_if_needed(
    db: Session, poll: Poll, current_time: datetime
) -> None:
    """сохраняет auto-close в базе, если время истекло"""

    if poll.closed_at is not None:
        return
    if poll.closes_at is None or _to_utc(poll.closes_at) > current_time:
        return

    poll.closed_at = current_time
    db.commit()
    db.refresh(poll)


def _utcnow() -> datetime:
    """возвращает текущее время в utc"""

    return datetime.now(timezone.utc)


def _to_utc(value: datetime) -> datetime:
    """нормализует дату к utc"""

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
