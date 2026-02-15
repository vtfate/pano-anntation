# app/controllers/image.py
import os
import uuid
import cv2
import numpy as np
import base64
import shutil
import math
from fastapi import UploadFile, HTTPException
from app.models.image import Image360, Annotation
from app.schemas.image import AnnotationCreate

from app.utils.ImageRecorder import ImageRecorder

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ImageController:
    @classmethod
    async def upload_image(cls, project_id: int, file: UploadFile):
        ext = file.filename.split('.')[-1]
        new_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, new_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        img = cv2.imread(file_path)
        h, w = img.shape[:2] if img is not None else (None, None)
        return await Image360.create(project_id=project_id, filename=file.filename, file_path=file_path,
                                     url=f"/static/uploads/{new_name}", width=w, height=h)

    @classmethod
    async def get_images_by_project(cls, project_id: int):
        return await Image360.filter(project_id=project_id).order_by("-created_at")

    @classmethod
    async def create_annotation(cls, image_id: int, obj_in: AnnotationCreate, annotator_id: int = 1):
        img_obj = await Image360.get(id=image_id)
        if not img_obj or not img_obj.width or not img_obj.height:
            raise HTTPException(status_code=400, detail="图片不存在或尺寸丢失")

        W, H = img_obj.width, img_obj.height

        # 1. 将 2D 画布的旋转框，逆向投影为 5-DOF 球面坐标 (RBFoV)
        spherical_data = cls._calculate_spherical_rbfov(
            crop_theta=obj_in.crop_theta,
            crop_phi=obj_in.crop_phi,
            crop_fov=obj_in.crop_fov,
            box_x=obj_in.box_x,
            box_y=obj_in.box_y,
            box_w=obj_in.box_w,
            box_h=obj_in.box_h,
            box_angle=obj_in.box_angle,
            out_w=512,  # 你的前端画布宽度
            out_h=512  # 你的前端画布高度
        )

        recorder = ImageRecorder(W, H, view_angle_w=spherical_data["fov_w"], view_angle_h=spherical_data["fov_h"],
                                 long_side=max(W, H))

        # 将球面中心坐标传入，并开启 border_only 模式，只拿边缘点阵
        Px, Py = recorder._sample_points(
            x=spherical_data["center_theta"],
            y=spherical_data["center_phi"],
            border_only=True
        )

        # 组装给前端 SVG <polygon> 画图的点集
        boundary_points = []
        for i in range(len(Px)):
            # 过滤掉无穷大或非法的点
            if not np.isnan(Px[i]) and not np.isnan(Py[i]):
                boundary_points.append({"x": float(Px[i]), "y": float(Py[i])})

        # 3. 存入数据库
        anno = await Annotation.create(
            image_id=image_id,
            annotator_id=annotator_id,
            label_id=obj_in.label_id,

            # 存真实球面坐标
            center_theta=spherical_data["center_theta"],
            center_phi=spherical_data["center_phi"],
            fov_w=spherical_data["fov_w"],
            fov_h=spherical_data["fov_h"],
            gamma=spherical_data["gamma"],

            # 存原始 2D 数据方便溯源
            box_x=obj_in.box_x,
            box_y=obj_in.box_y,
            box_w=obj_in.box_w,
            box_h=obj_in.box_h,
            box_angle=obj_in.box_angle
        )

        return {
            "id": anno.id,
            "image_id": anno.image_id_id,  # tortoise-orm 外键特殊后缀
            "label_id": anno.label_id_id,
            "annotator_id": anno.annotator_id,
            "center_theta": anno.center_theta,
            "center_phi": anno.center_phi,
            "fov_w": anno.fov_w,
            "fov_h": anno.fov_h,
            "gamma": anno.gamma,
            "boundary_points": boundary_points,  # 🌟 灵魂数据：像素点集
            "created_at": anno.created_at
        }

    # 从 2D 切图参数 -> 球面 RBFoV 参数
    @staticmethod
    def _calculate_spherical_rbfov(crop_theta, crop_phi, crop_fov, box_x, box_y, box_w, box_h, box_angle, out_w, out_h):
        # 1. 焦距 f
        f = 0.5 * out_w / np.tan(0.5 * np.radians(crop_fov))
        cx = box_x + box_w / 2.0
        cy = box_y + box_h / 2.0

        # 3. 转换为相机 3D 射线
        x_c = cx - out_w / 2.0
        y_c = -(cy - out_h / 2.0)
        z_c = f
        v_cam = np.array([x_c, y_c, z_c])

        # 4. 根据切图视角，构建旋转矩阵，投射回绝对球面
        rx = np.array([[1, 0, 0], [0, np.cos(crop_phi), -np.sin(crop_phi)], [0, np.sin(crop_phi), np.cos(crop_phi)]])
        ry = np.array(
            [[np.cos(-crop_theta), 0, np.sin(-crop_theta)], [0, 1, 0], [-np.sin(-crop_theta), 0, np.cos(-crop_theta)]])
        R = np.dot(ry, rx)
        v_world = np.dot(R, v_cam)

        x_r, y_r, z_r = v_world[0], v_world[1], v_world[2]

        # 5. 获得真实的绝对中心 Theta 和 Phi (弧度)
        norm_r = np.sqrt(x_r ** 2 + y_r ** 2 + z_r ** 2)
        final_phi = np.arcsin(np.clip(y_r / norm_r, -1.0, 1.0))
        final_theta = np.arctan2(x_r, z_r)

        # 6. 计算真实水平/垂直 FOV 宽度 (张角)
        fov_w_rad = 2 * np.arctan((box_w / 2.0) / f)
        fov_h_rad = 2 * np.arctan((box_h / 2.0) / f)

        gamma_rad = np.radians(box_angle)

        return {
            "center_theta": float(final_theta),
            "center_phi": float(final_phi),
            "fov_w": float(np.degrees(fov_w_rad)),
            "fov_h": float(np.degrees(fov_h_rad)),
            "gamma": float(gamma_rad)
        }

    # 全景图局部切片算法
    @classmethod
    async def get_perspective_crop(cls, image_id: int, u: float, v: float, fov: float = 90.0):
        img_obj = await Image360.get_or_none(id=image_id)
        if not img_obj or not os.path.exists(img_obj.file_path):
            raise HTTPException(status_code=404, detail="图片不存在")
        img = cv2.imread(img_obj.file_path)
        if img is None:
            raise HTTPException(status_code=500, detail="图片解码失败")
        H, W = img.shape[:2]
        center_theta = (u / W) * 2 * np.pi - np.pi
        center_phi = (H / 2 - v) / (H / 2) * (np.pi / 2)
        perspective_img = cls._equirectangular_to_perspective(img, center_theta, center_phi, fov, 512, 512)
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
        _, buffer = cv2.imencode('.jpg', perspective_img, encode_params)
        img_str = base64.b64encode(buffer).decode('utf-8')
        return {
            "image_base64": f"data:image/jpeg;base64,{img_str}",
            "center_theta": float(center_theta),
            "center_phi": float(center_phi),
            "fov": float(fov)
        }

    @staticmethod
    def _equirectangular_to_perspective(img, theta_center, phi_center, fov, out_w, out_h):
        H, W = img.shape[:2]
        f = 0.5 * out_w / np.tan(0.5 * np.radians(fov))
        cx, cy = out_w / 2, out_h / 2
        x_grid, y_grid = np.meshgrid(np.arange(out_w, dtype=np.float32), np.arange(out_h, dtype=np.float32))
        x_3d = x_grid - cx
        y_3d = -(y_grid - cy)
        z_3d = np.full_like(x_3d, f)
        vectors = np.stack([x_3d, y_3d, z_3d], axis=-1).reshape(-1, 3)
        rx = np.array(
            [[1, 0, 0], [0, np.cos(phi_center), -np.sin(phi_center)], [0, np.sin(phi_center), np.cos(phi_center)]])
        ry = np.array([[np.cos(-theta_center), 0, np.sin(-theta_center)], [0, 1, 0],
                       [-np.sin(-theta_center), 0, np.cos(-theta_center)]])
        R = np.dot(ry, rx)
        xyz_rotated = np.dot(R, vectors.T).T
        x_r, y_r, z_r = xyz_rotated[:, 0], xyz_rotated[:, 1], xyz_rotated[:, 2]
        norm_r = np.sqrt(x_r ** 2 + y_r ** 2 + z_r ** 2)
        phi_map = np.arcsin(np.clip(y_r / norm_r, -1, 1))
        theta_map = np.arctan2(x_r, z_r)
        u_src = (theta_map + np.pi) / (2 * np.pi) * W
        v_src = (np.pi / 2 - phi_map) / np.pi * H
        u_src = np.mod(u_src, W)
        v_src = np.clip(v_src, 0, H - 1)
        map_x = u_src.reshape(out_h, out_w).astype(np.float32)
        map_y = v_src.reshape(out_h, out_w).astype(np.float32)
        return cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)