import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise
from fastapi.staticfiles import StaticFiles

from app.core.exceptions import SettingNotFound
from app.core.init_app import (
    init_data,
    make_middlewares,
    register_exceptions,
    register_routers,
)

try:
    from app.settings.config import settings
except ImportError:
    raise SettingNotFound("Can not import settings")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_data()
    yield
    await Tortoise.close_connections()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.VERSION,
        openapi_url="/openapi.json",
        middleware=make_middlewares(),
        lifespan=lifespan,
    )
    register_exceptions(app)
    register_routers(app, prefix="/api")
    STATIC_DIR =  os.path.abspath(os.path.join(os.getcwd(), "static"))
    os.makedirs(os.path.join(STATIC_DIR, "uploads"), exist_ok=True)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
