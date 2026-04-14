from fastapi import Header

from app.core.config import settings
from app.core.errors import UnauthorizedError

X_USER_ID_HEADER = settings.user_id_header_name


def get_current_user_id(
    x_user_id: str = Header(..., alias=X_USER_ID_HEADER),
) -> str:
    """возвращает id текущего пользователя из обязательного заголовка"""

    user_id = x_user_id.strip()
    if not user_id:
        raise UnauthorizedError(
            code="authentication_required",
            message=f"Заголовок {X_USER_ID_HEADER} не может быть пустым",
            details={"header": X_USER_ID_HEADER},
        )

    return user_id
