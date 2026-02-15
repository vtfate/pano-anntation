# app/schemas/project.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# --- Label 标签相关 ---
class LabelCreate(BaseModel):
    name: str
    color: str = "#18a058"

class LabelOut(LabelCreate):
    id: int
    project_id: int
    created_at: datetime
    class Config:
        from_attributes = True

# --- Project 项目相关 ---
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectOut(ProjectCreate):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True