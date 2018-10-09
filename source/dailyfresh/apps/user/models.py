from django.db import models
from django.contrib.auth.models import AbstractUser

from db.basemodel import BaseModel


class User(AbstractUser, BaseModel):
    """用户模型"""

    class Meta:
        db_table = 'df_user'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username


class AddressManager(models.Manager):
    """自定义Address模型管理器"""

    def get_default_address(self, user):
        try:
            addr = Address.objects.get(user_id=user.id, is_default=True)
        except Address.DoesNotExist:
            addr = None

        return addr

class Address(BaseModel):
    """用户地址模型"""
    user = models.ForeignKey('User', verbose_name='所属账户', on_delete=models.CASCADE)
    receiver = models.CharField(max_length=20, verbose_name='收件人')
    addr = models.CharField(max_length=128, verbose_name='收件地址')
    zip_code = models.CharField(max_length=6, verbose_name='邮编')
    phone = models.CharField(max_length=11, verbose_name='联系方式')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    objects = AddressManager()
    class Meta:
        db_table = 'df_address'
        verbose_name = '地址'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user
