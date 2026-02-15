import cv2
import numpy as np
import base64
import os
from app.models.image import Image360


class ToolController:

    @classmethod
    async def get_perspective_crop(cls, image_id: int, u: float, v: float, fov: float = 90, out_w: int = 512,
                                   out_h: int = 512):
        """
        获取全景图的透视投影切片 (Core Logic)
        """
        # 1. 查询数据库获取图片路径
        img_obj = await Image360.get(id=image_id)
        if not img_obj or not os.path.exists(img_obj.file_path):
            raise FileNotFoundError(f"Image not found: ID {image_id}")

        # 2. 读取图片 (OpenCV 读取默认为 BGR)
        # 生产环境中建议使用缓存或对象存储读取，避免频繁磁盘 IO
        img = cv2.imread(img_obj.file_path)
        if img is None:
            raise ValueError("Failed to decode image file")

        H, W = img.shape[:2]

        # 3. 计算点击中心的球坐标 (theta, phi)
        # theta (经度):范围 [-pi, pi], 对应图像宽度 [0, W]
        # phi (纬度): 范围 [-pi/2, pi/2], 对应图像高度 [0, H] (注意图像Y轴向下，需要反转)
        center_theta = (u / W) * 2 * np.pi - np.pi
        center_phi = (H / 2 - v) / (H / 2) * (np.pi / 2)

        # 4. 调用数学核心算法生成切片
        perspective_img = cls._equirectangular_to_perspective(
            img, center_theta, center_phi, fov, out_w, out_h
        )

        # 5. 转为 Base64 字符串返回给前端
        # 使用 .jpg 格式可以减小传输体积，质量设为 90
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
        """
        [数学核心] 全景图(ERP) -> 透视投影(Perspective)
        使用逆向映射法 (Inverse Mapping) + 3D 旋转矩阵
        """
        H, W = img.shape[:2]

        # --- A. 相机参数 ---
        # 根据 FoV 计算焦距 f
        # f = (W / 2) / tan(FoV / 2)
        f = 0.5 * out_w / np.tan(0.5 * np.radians(fov))

        # --- B. 生成目标图像的网格坐标 (Camera Coordinates) ---
        cx, cy = out_w / 2, out_h / 2
        x_range = np.arange(out_w, dtype=np.float32)
        y_range = np.arange(out_h, dtype=np.float32)
        x_grid, y_grid = np.meshgrid(x_range, y_range)

        # 将像素坐标转换为 3D 向量 (x, y, z)
        # 假设虚拟相机看向 Z 轴正方向
        x_3d = x_grid - cx
        y_3d = -(y_grid - cy)  # 图像坐标 y 向下，3D 坐标 y 向上，故取反
        z_3d = np.full_like(x_3d, f)

        # 将向量展平以便进行矩阵乘法: (N, 3)
        vectors = np.stack([x_3d, y_3d, z_3d], axis=-1).reshape(-1, 3)

        # --- C. 构建旋转矩阵 R ---
        # 我们需要将“看向正前方”的视线，旋转到指向 (theta_center, phi_center)

        # 1. 绕 X 轴旋转 (Pitch/Phi)
        # 向上看是正角度
        rx = np.array([
            [1, 0, 0],
            [0, np.cos(phi_center), -np.sin(phi_center)],
            [0, np.sin(phi_center), np.cos(phi_center)]
        ])

        # 2. 绕 Y 轴旋转 (Yaw/Theta)
        # 向右看是正角度 (注意坐标系定义，这里通常是绕 Y 轴逆时针)
        # 为了匹配全景图的经度方向，通常使用 -theta
        ry = np.array([
            [np.cos(-theta_center), 0, np.sin(-theta_center)],
            [0, 1, 0],
            [-np.sin(-theta_center), 0, np.cos(-theta_center)]
        ])

        # 组合旋转矩阵 R = Ry * Rx
        R = np.dot(ry, rx)

        # --- D. 应用旋转并映射回球面 ---
        # (3, 3) @ (3, N) -> (3, N) -> Transpose back to (N, 3)
        xyz_rotated = np.dot(R, vectors.T).T

        # 提取旋转后的坐标
        x_r = xyz_rotated[:, 0]
        y_r = xyz_rotated[:, 1]
        z_r = xyz_rotated[:, 2]

        # 计算球面坐标 (theta, phi)
        # 模长 norm
        norm_r = np.sqrt(x_r ** 2 + y_r ** 2 + z_r ** 2)

        # phi (纬度) = arcsin(y / R)
        # 使用 clip 防止浮点误差导致数值超出 [-1, 1]
        phi_map = np.arcsin(np.clip(y_r / norm_r, -1, 1))

        # theta (经度) = arctan2(x, z)
        theta_map = np.arctan2(x_r, z_r)

        # --- E. 映射回原图像素坐标 (u, v) ---
        # 经度 [-pi, pi] -> [0, W]
        u_src = (theta_map + np.pi) / (2 * np.pi) * W

        # 纬度 [-pi/2, pi/2] -> [0, H] (注意 y 轴反转：pi/2 对应 0)
        v_src = (np.pi / 2 - phi_map) / np.pi * H

        # --- F. 处理边界循环 (Wrap Around) ---
        # 全景图左右是相通的，必须用取模运算处理边界
        u_src = np.mod(u_src, W)

        # 至于上下边界，clip 到图像范围内即可
        v_src = np.clip(v_src, 0, H - 1)

        # Reshape 回图像尺寸，准备给 cv2.remap 使用
        map_x = u_src.reshape(out_h, out_w).astype(np.float32)
        map_y = v_src.reshape(out_h, out_w).astype(np.float32)

        # --- G. 重映射 (Remap) ---
        # 使用双线性插值 (INTER_LINEAR) 获得平滑效果
        perspective_img = cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

        return perspective_img