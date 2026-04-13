from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PollCreateRequest(BaseModel):
    """запрос на создание опроса"""

    question: str = Field(min_length=1)
    options: list[str]
    close_after_seconds: int | None = Field(default=None, ge=1)

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        """проверяет вопрос"""

        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Вопрос не может быть пустым")
        return cleaned

    @field_validator("options")
    @classmethod
    def validate_options(cls, value: list[str]) -> list[str]:
        """проверяет варианты ответа"""

        cleaned_options = [option.strip() for option in value]
        if len(cleaned_options) < 2:
            raise ValueError("Должно быть минимум 2 варианта ответа")
        if len(cleaned_options) > 5:
            raise ValueError("Должно быть максимум 5 вариантов ответа")
        if any(not option for option in cleaned_options):
            raise ValueError("Варианты ответа не могут быть пустыми")
        return cleaned_options


class PollVoteRequest(BaseModel):
    """запрос на голосование"""

    option_id: int = Field(gt=0)


class PollOptionResponse(BaseModel):
    """вариант ответа"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    text: str


class PollCreatedResponse(BaseModel):
    """ответ на создание опроса"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question: str
    status: str
    closes_at: datetime | None
    options: list[PollOptionResponse]


class PollListItemResponse(BaseModel):
    """элемент списка опросов"""

    id: int
    question: str
    status: str
    options_count: int
    total_votes: int
    closes_at: datetime | None
    created_at: datetime


class PollListResponse(BaseModel):
    """список опросов"""

    items: list[PollListItemResponse]


class VoteCreatedResponse(BaseModel):
    """ответ на успешное голосование"""

    poll_id: int
    option_id: int
    status: str


class PollResultOptionResponse(BaseModel):
    """вариант ответа с количеством голосов"""

    id: int
    text: str
    votes_count: int


class PollResultsResponse(BaseModel):
    """результаты опроса"""

    id: int
    question: str
    status: str
    total_votes: int
    closes_at: datetime | None
    options: list[PollResultOptionResponse]


class PollClosedResponse(BaseModel):
    """ответ на закрытие опроса"""

    id: int
    status: str
    closed_at: datetime


class PollCreateInternal(BaseModel):
    """внутренняя модель создания опроса"""

    question: str
    options: list[str]
    closes_at: datetime | None

    @classmethod
    def from_request(cls, request: PollCreateRequest) -> "PollCreateInternal":
        """строит внутреннюю модель из запроса"""

        closes_at = None
        if request.close_after_seconds is not None:
            closes_at = datetime.now(timezone.utc) + timedelta(
                seconds=request.close_after_seconds
            )
        return cls(
            question=request.question,
            options=request.options,
            closes_at=closes_at,
        )
