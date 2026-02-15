# app/api/v1/project.py
from fastapi import APIRouter
from typing import List
from app.controllers.project import ProjectController
from app.schemas.project import ProjectCreate, ProjectOut, LabelCreate, LabelOut

router = APIRouter()

@router.get("/list", response_model=List[ProjectOut], summary="获取所有项目")
async def get_projects():
    return await ProjectController.get_all_projects()

@router.post("/create", response_model=ProjectOut, summary="创建新项目")
async def create_project(project_in: ProjectCreate):
    return await ProjectController.create_project(project_in)

@router.get("/{project_id}/labels", response_model=List[LabelOut], summary="获取项目的标签列表")
async def get_labels(project_id: int):
    return await ProjectController.get_project_labels(project_id)

@router.post("/{project_id}/labels", response_model=LabelOut, summary="为项目创建标签")
async def create_label(project_id: int, label_in: LabelCreate):
    return await ProjectController.create_label(project_id, label_in)

@router.delete("/labels/{label_id}", summary="删除标签")
async def delete_label(label_id: int):
    return await ProjectController.delete_label(label_id)