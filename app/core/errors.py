from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """бизнес-ошибка приложения"""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    """ошибка отсутствующего ресурса"""

    def __init__(
        self, code: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            status_code=404, code=code, message=message, details=details
        )


class ConflictError(AppError):
    """ошибка конфликтного состояния"""

    def __init__(
        self, code: str, message: str, details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(
            status_code=409, code=code, message=message, details=details
        )


def build_error_response(
    status_code: int, code: str, message: str, details: Dict[str, Any]
) -> JSONResponse:
    """строит единый ответ с ошибкой"""

    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """регистрирует обработчики ошибок"""

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return build_error_response(
            exc.status_code, exc.code, exc.message, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {
            "fields": [
                {
                    "field": ".".join(
                        str(part) for part in error["loc"] if part != "body"
                    ),
                    "message": error["msg"],
                }
                for error in exc.errors()
            ]
        }
        return build_error_response(
            422,
            "validation_error",
            "Запрос не прошел валидацию",
            details,
        )
