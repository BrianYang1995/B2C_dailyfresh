from django.conf.urls import url
from order.views import OrderPlaceView


urlpatterns = [
    url(r'^$', OrderPlaceView.as_view(), name='show'),
]
