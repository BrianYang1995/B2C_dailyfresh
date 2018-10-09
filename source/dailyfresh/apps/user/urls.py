from django.conf.urls import url
from user.views import RegisterView, ActiveView, LoginView, UserAddressView, UserBaseInfoView, UserOrderView, LogoutView

from django.contrib.auth.decorators import login_required


urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 用户注册
    url(r'active/(?P<token>.*)$', ActiveView.as_view(), name='active'),  # 用户激活
    url(r'login/$', LoginView.as_view(), name='login'),  # 用户登录
    url(r'logout/$', LogoutView.as_view(), name='logout'),  # 用户登录

    # url(r'^$', login_required(UserBaseInfoView.as_view()), name='user'),  # 用户中心基本信息页
    # url(r'^address$', login_required(UserAddressView.as_view()), name='address'),  # 用户中心地址页
    # url(r'^order$', login_required(UserOrderView.as_view()), name='order'),  # 用户中心订单页

    url(r'^$', UserBaseInfoView.as_view(), name='user'),  # 用户中心基本信息页
    url(r'^address$', UserAddressView.as_view(), name='address'),  # 用户中心地址页
    url(r'^order$', UserOrderView.as_view(), name='order'),  # 用户中心订单页

]
