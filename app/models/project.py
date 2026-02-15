# app/models/project.py
from tortoise import fields
from app.models.base import BaseModel, TimestampMixin


class Project(BaseModel, TimestampMixin):
    """标注项目表"""
    name = fields.CharField(max_length=100, description="项目名称", index=True)
    description = fields.CharField(max_length=500, null=True, description="项目描述")

    # 反向关联 (用于方便地查询项目下的标签和图片)
    labels: fields.ReverseRelation["Label"]
    images: fields.ReverseRelation["Image360"]

    class Meta:
        table = "project"


class Label(BaseModel, TimestampMixin):
    """项目标签表"""
    # 关联到项目：级联删除（项目删了，标签也没了）
    project = fields.ForeignKeyField('models.Project', related_name='labels', on_delete=fields.CASCADE,
                                     description="所属项目")

    name = fields.CharField(max_length=50, description="标签名称 (如 chair)")
    color = fields.CharField(max_length=20, default="#18a058", description="标签颜色 (Hex值)")

    # 反向关联 (用于查询使用了这个标签的所有标注)
    annotations: fields.ReverseRelation["Annotation"]

    class Meta:
        table = "label"