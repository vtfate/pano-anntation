# app/schemas/image.py
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


# --- 全景图本身相关 ---
class Image360Out(BaseModel):
    id: int
    project_id: int
    filename: str
    url: str
    width: Optional[int]
    height: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# --- 局部透视切图请求 ---
class PerspectiveRequest(BaseModel):
    image_id: int
    u: float
    v: float
    fov: float = 90.0


class AnnotationCreate(BaseModel):
    label_id: int

    crop_theta: float
    crop_phi: float
    crop_fov: float

    box_x: float
    box_y: float
    box_w: float
    box_h: float
    box_angle: float = 0.0  # 新增：2D框的旋转角度 (前端通常传角度度数)

class AnnotationOut(BaseModel):
    id: int
    image_id: int
    label_id: int
    annotator_id: Optional[int]

    # RBFoV
    center_theta: float
    center_phi: float
    fov_w: float
    fov_h: float
    gamma: float

    # 用于前端 SVG完美渲染曲率边界的 2D 像素点阵序列
    boundary_points: List[Dict[str, float]]

    created_at: datetime

    class Config:
        from_attributes = True