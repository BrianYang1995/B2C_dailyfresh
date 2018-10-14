from django.shortcuts import render, HttpResponse, redirect
from django.views.generic import View
from utils.mixin import LoginRequestMixIn
from goods.models import GoodsSKU
from user.models import Address

from django_redis import get_redis_connection


class OrderPlaceView(LoginRequestMixIn, View):
    """显示订单页"""
    def post(self, request):
        # 获取数据
        user = request.user
        goods_skus = request.POST.getlist('goods_skus')
        if not goods_skus:
            return redirect('cart:show')

        # 收获地址
        addrs = Address.objects.filter(user=user)

        # 查询数据
        goods_list = []
        user_key = 'cart_%s' % user.id
        count = 0  # 总数
        amount_price = 0  # 商品总价
        conn = get_redis_connection('default')

        for sku_id in goods_skus:
            goods = GoodsSKU.objects.get(id=sku_id)

            # 获取商品数目，添加动态属性
            goods_count = conn.hget(user_key, sku_id)
            count += int(goods_count)
            goods.goods_count = int(goods_count)
            # 商品价格小计，添加动态属性
            total_price = goods.price * int(goods_count)
            goods.total_price = total_price
            amount_price += total_price

            goods_list.append(goods)

        transite_price = 12
        total_pay = amount_price + transite_price

        # 上下文
        context = {
            'goods_list': goods_list,
            'count': count,
            'amount_price': amount_price,
            'transite_price': transite_price,
            'total_pay': total_pay,
            'addrs': addrs
        }
        return render(request, 'place_order.html', context)

