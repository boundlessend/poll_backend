from fastapi import Header

from app.core.errors import UnauthorizedError


def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> str:
    """возвращает id текущего пользователя из заголовка"""

    if x_user_id is None:
        raise UnauthorizedError(
            code="authentication_required",
            message="Для этого действия нужен заголовок X-User-Id",
            details={"header": "X-User-Id"},
        )

    user_id = x_user_id.strip()
    if not user_id:
        raise UnauthorizedError(
            code="authentication_required",
            message="Заголовок X-User-Id не может быть пустым",
            details={"header": "X-User-Id"},
        )

    return user_id
