from django.conf.urls import url
from user.views import RegisterView, ActiveView


urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 用户注册
    url(r'active/(?P<token>.*)', ActiveView.as_view(), name='active') # 用户激活
]
