from fastapi import APIRouter

from .project import router

project_router = APIRouter()
project_router.include_router(router, tags=["项目模块"])

__all__ = ["project_router"]
