from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

MOSCOW_TZ = ZoneInfo(settings.timezone_name)


def get_moscow_now() -> datetime:
    """возвращает текущее время в москве"""

    return datetime.now(MOSCOW_TZ)


def to_moscow(value: datetime | None) -> datetime | None:
    """нормализует дату к московскому времени"""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=MOSCOW_TZ)
    return value.astimezone(MOSCOW_TZ)
