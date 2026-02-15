from fastapi import APIRouter

from .image import router

image_router = APIRouter()
image_router.include_router(router, tags=["全景图像模块"])

__all__ = ["image_router"]
