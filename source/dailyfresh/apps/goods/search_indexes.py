# coding=utf-8
from haystack import indexes
from goods.models import GoodsSKU  # 引入模型类


class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    """商品索引类"""
    # 生成索引文件的字段
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):   # 固定用法，返回模型类
        return GoodsSKU

    def index_queryset(self, using=None):
        return self.get_model().objects.all()  # 固定用法，返回查询语句