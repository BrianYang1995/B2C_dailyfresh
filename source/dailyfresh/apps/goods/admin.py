from django.contrib import admin
from django.core.cache import cache
from goods.models import (
    GoodsType, GoodsSKU, Goods, GoodsImage, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner
)




class BaseAdmin(admin.ModelAdmin):
    """用于重新生成静态页面"""
    def save_model(self, request, obj, form, change):
        """Admin保存数据时触发"""
        super().save_model(request, obj, form, change)
        self.generate_static_index_html()

    def delete_model(self, request, obj):
        """Admin删除数据时触发"""
        super().delete_model(request, obj)
        self.generate_static_index_html()

    def generate_static_index_html(self):
        """触发异步任务"""
        from celery_task.tasks import generate_index_html
        generate_index_html.delay()
        cache.delete('static_index_data')


class GoodsTypeAdmin(BaseAdmin):
    pass


class IndexGoodsBannerAdmin(BaseAdmin):
    pass


class IndexPromotionBannerAdmin(BaseAdmin):
    pass


class IndexTypeGoodsBannerAdmin(BaseAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(GoodsSKU)
admin.site.register(Goods)
admin.site.register(GoodsImage)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
