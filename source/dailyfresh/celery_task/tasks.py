from celery import Celery

from django.core.mail import send_mail
from django.conf import settings

# worker端django启动文件
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()
#
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