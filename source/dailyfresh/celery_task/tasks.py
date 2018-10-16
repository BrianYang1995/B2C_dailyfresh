from celery import Celery

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import get_template

# worker端django启动文件
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
django.setup()



from goods.models import (
    GoodsType, GoodsSKU, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
)

# 创建celery对象
app = Celery('celery_task.tasks', broker='redis://127.0.0.1:6379/10')


@app.task()
def send_register_active_email(receiver, username, token):
    """任务处理函数"""
    subject = '欢迎注册天天生鲜'
    message = ''
    from_email = settings.EMAIL_HOST_USER
    html_message = '<h2>欢迎%s注册天天生鲜</h2>点击下面邮箱激活<p><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s</a></p>' % (
    username, token, token)

    send_mail(subject, message, from_email, [receiver], html_message=html_message)


@app.task()
def generate_index_html():
    """生成首页静态页面"""
    # 商品分类
    try:
        types = GoodsType.objects.all()
    except Exception:
        pass

    # 轮播图
    try:
        goods_banner = IndexGoodsBanner.objects.all().order_by('index')[:4]
    except Exception:
        pass

    # 促销活动
    try:
        promotion = IndexPromotionBanner.objects.all().order_by('index')[:2]
    except Exception:
        pass

    # 商品列表
    for type in types:
        try:
            text_goods_list = IndexTypeGoodsBanner.objects.filter(display_type=0, type=type).order_by('index').all()[:3]
            image_goods_list = IndexTypeGoodsBanner.objects.filter(display_type=1, type=type).order_by('index').all()[:4]
            type.text_goods_list = text_goods_list
            type.image_goods_list = image_goods_list
        except Exception:
            pass

    # 上下文处理
    content = {
        'types': types,
        'goods_banner': goods_banner,
        'promotion': promotion,
    }

    template = get_template('index.html')
    static_index_html = template.render(content)

    path = os.path.join(settings.BASE_DIR, 'static/index.html')

    with open(path, 'w') as f:
        f.write(static_index_html)

