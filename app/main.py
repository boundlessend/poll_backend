from fastapi import FastAPI

from app.api.polls import router as polls_router
from app.core.config import settings
from app.core.errors import register_exception_handlers


app = FastAPI(title=settings.app_name)
register_exception_handlers(app)
app.include_router(polls_router, prefix=settings.api_v1_prefix)
