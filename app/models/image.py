# app/models/image.py
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class Image360(BaseModel, TimestampMixin):
    """全景图片源文件表"""
    # 关联到项目 (级联删除)
    project = fields.ForeignKeyField('models.Project', related_name='images', on_delete=fields.CASCADE,
                                     description="所属项目")

    filename = fields.CharField(max_length=255, description="原始文件名")
    file_path = fields.CharField(max_length=512, description="服务器存储路径")
    url = fields.CharField(max_length=512, description="访问URL")
    width = fields.IntField(null=True, description="图片真实宽度")
    height = fields.IntField(null=True, description="图片真实高度")

    # 反向关联
    annotations: fields.ReverseRelation["Annotation"]

    class Meta:
        table = "image_360"


class Annotation(BaseModel, TimestampMixin):
    """标注结果表"""
    # 关联到图片 (级联删除)
    image = fields.ForeignKeyField('models.Image360', related_name='annotations', on_delete=fields.CASCADE,
                                   description="所属图片")
    # 关联到具体的 Label 表
    label = fields.ForeignKeyField('models.Label', related_name='annotations', on_delete=fields.RESTRICT,
                                   description="所属标签")

    annotator_id = fields.IntField(description="标注人ID", null=True)

    #  RBFoV
    center_theta = fields.FloatField(description="中心点经度 (Theta, 弧度/角度均可，推荐保存弧度)")
    center_phi = fields.FloatField(description="中心点纬度 (Phi, 弧度/角度均可，推荐保存弧度)")
    fov_w = fields.FloatField(description="水平视场角 (FOV_W, 推荐保存角度)")
    fov_h = fields.FloatField(description="垂直视场角 (FOV_H, 推荐保存角度)")
    gamma = fields.FloatField(description="物体自转角度 (Gamma, 推荐保存弧度)", default=0.0)

    box_x = fields.FloatField(description="2D框 中心X坐标或左上角X", null=True)
    box_y = fields.FloatField(description="2D框 中心Y坐标或左上角Y", null=True)
    box_w = fields.FloatField(description="2D框 宽度", null=True)
    box_h = fields.FloatField(description="2D框 高度", null=True)
    box_angle = fields.FloatField(description="2D框 旋转角度", null=True, default=0.0)

    class Meta:
        table = "annotation"