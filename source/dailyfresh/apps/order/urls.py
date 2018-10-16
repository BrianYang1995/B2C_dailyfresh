from django.conf.urls import url
from order.views import OrderPlaceView, OrderCommitView, OrderPayView, OrderCheckView, CommentView


urlpatterns = [
    url(r'^$', OrderPlaceView.as_view(), name='show'),
    url(r'^commit$', OrderCommitView.as_view(), name='commit'),
    url(r'^pay$', OrderPayView.as_view(), name='pay'),
    url(r'^check$', OrderCheckView.as_view(), name='check'),
    url(r'^comment/(?P<order_id>.+)$', CommentView.as_view(), name='comment'),  # 订单评论

]
