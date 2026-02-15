# app/controllers/project.py
from app.models.project import Project, Label
from app.schemas.project import ProjectCreate, LabelCreate

class ProjectController:
    @classmethod
    async def get_all_projects(cls):
        return await Project.all().order_by("-created_at")

    @classmethod
    async def create_project(cls, obj_in: ProjectCreate):
        return await Project.create(**obj_in.model_dump())

    @classmethod
    async def get_project_labels(cls, project_id: int):
        return await Label.filter(project_id=project_id).order_by("-created_at")

    @classmethod
    async def create_label(cls, project_id: int, obj_in: LabelCreate):
        return await Label.create(project_id=project_id, **obj_in.model_dump())

    @classmethod
    async def delete_label(cls, label_id: int):
        await Label.filter(id=label_id).delete()
        return {"msg": "删除成功"}