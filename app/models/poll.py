from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Poll(Base):
    """опрос"""

    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    closes_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    options: Mapped[list["PollOption"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PollOption.id",
    )
    votes: Mapped[list["Vote"]] = relationship(
        back_populates="poll",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def status(self) -> str:
        """возвращает актуальный статус опроса"""

        now = datetime.now(timezone.utc)
        if self.closed_at is not None:
            return "closed"
        if self.closes_at is not None and self._to_utc(self.closes_at) <= now:
            return "closed"
        return "open"

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        """нормализует дату к utc"""

        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class PollOption(Base):
    """вариант ответа в опросе"""

    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)

    poll: Mapped[Poll] = relationship(back_populates="options")
    votes: Mapped[list["Vote"]] = relationship(back_populates="option")


class Vote(Base):
    """голос пользователя"""

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("poll_id", "user_id", name="uq_votes_poll_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[int] = mapped_column(
        ForeignKey("polls.id", ondelete="CASCADE"),
        nullable=False,
    )
    option_id: Mapped[int] = mapped_column(
        ForeignKey("poll_options.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    poll: Mapped[Poll] = relationship(back_populates="votes")
    option: Mapped[PollOption] = relationship(back_populates="votes")
