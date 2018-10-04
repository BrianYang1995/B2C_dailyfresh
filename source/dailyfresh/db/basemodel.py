from django.db import models


class BaseModel(models.Model):
    """所有模型的基类"""
    create_date = models.DateField(auto_now_add=True, verbose_name='创建时间')
    update_date = models.DateField(auto_now=True, verbose_name='更新时间')
    is_delete = models.BooleanField(verbose_name='删除标记', default=False)

    class Meta:
        """构造模型类：必须有"""
        abstract = True