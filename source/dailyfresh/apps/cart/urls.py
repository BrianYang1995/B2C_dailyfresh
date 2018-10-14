from django.conf.urls import url
from cart.views import CartAddView, Cart, CartChangeView, CartDeleteView

urlpatterns = [
    url(r'^add$', CartAddView.as_view(), name='add'),
    url(r'^$', Cart.as_view(), name='show'),
    url(r'^change$', CartChangeView.as_view(), name='change'),
    url(r'^delete$', CartDeleteView.as_view(), name='delete'),
]
