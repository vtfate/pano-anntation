# app/api/v1/image.py
from fastapi import APIRouter, UploadFile, File, Form
from typing import List
from app.controllers.image import ImageController
from app.schemas.image import Image360Out, PerspectiveRequest, AnnotationCreate, AnnotationOut

router = APIRouter()

@router.post("/upload", response_model=Image360Out, summary="上传全景图到指定项目")
async def upload_image(
    project_id: int = Form(..., description="所属项目ID"),
    file: UploadFile = File(..., description="全景图文件")
):
    # 注意：文件上传时，如果需要带额外参数，FastAPI 推荐使用 Form 表单格式
    return await ImageController.upload_image(project_id, file)

@router.get("/list", response_model=List[Image360Out], summary="获取某项目下的所有图片")
async def get_images(project_id: int):
    return await ImageController.get_images_by_project(project_id)

@router.post("/crop", summary="获取透视切片 (核心算法)")
async def get_perspective_crop(req: PerspectiveRequest):
    return await ImageController.get_perspective_crop(req.image_id, req.u, req.v, req.fov)

@router.post("/{image_id}/annotate", response_model=AnnotationOut, summary="保存标注结果")
async def save_annotation(image_id: int, obj_in: AnnotationCreate):
    return await ImageController.create_annotation(image_id, obj_in)