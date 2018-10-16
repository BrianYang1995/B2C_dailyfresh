from django.shortcuts import render, redirect
from django.views.generic import View
from django.http import JsonResponse

from goods.models import GoodsSKU
from utils.mixin import LoginRequestMixIn

from django_redis import get_redis_connection


class CartAddView(View):
    """添加购物车"""
    def post(self, request):
        """接收数据，并添加购物车"""

        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')
        sku_count = request.POST.get('sku_count')

        # 校验数据
        try:
            goods = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '商品不存在'})

        try:
            sku_count = int(sku_count)
        except Exception:
            return JsonResponse({'res': 2, 'errmsg': '商品数量出错'})

        if sku_count <= 0:
            return JsonResponse({'res': 2, 'errmsg': '商品数量出错'})

        if goods.stock < sku_count:
            return JsonResponse({'res': 2, 'errmsg': '库存不足'})

        # 加入购物车
        user_key = 'cart_%s' % user.id

        conn = get_redis_connection('default')
        count = conn.hget(user_key, sku_id)
        if count:
            sku_count = sku_count + int(count)
        conn.hset(user_key, sku_id, sku_count)
        keys = conn.hkeys(user_key)
        print(len(keys))

        return JsonResponse({'res': 9, 'message': '添加成功', 'cart_count': len(keys)})


class Cart(LoginRequestMixIn, View):
    """显示购物车"""
    def get(self, request):
        """购物车页面"""
        # 获取数据
        user = request.user

        # 查询数据
        conn = get_redis_connection('default')
        user_key = 'cart_%s' % user.id
        cart_keys = conn.hkeys(user_key)
        goods_list = []
        count = 0
        amount_price = 0
        for goods_id in cart_keys:

            try:
                goods = GoodsSKU.objects.get(id=goods_id)
            except GoodsSKU.DoesNotExist:
                continue
            # 获取商品数目，添加动态属性
            goods_count = conn.hget(user_key, goods_id)
            count += int(goods_count)
            goods.goods_count = int(goods_count)
            # 商品价格小计，添加动态属性
            total_price = goods.price * int(goods_count)
            goods.total_price = total_price
            amount_price += total_price

            goods_list.append(goods)



        # 整理模板上下文
        context = {
            'count': count,
            'amount_price': amount_price,
            'goods_list': goods_list,
        }
        return  render(request, 'cart.html', context)


class CartChangeView(View):
    """修改商品数量"""
    def post(self, request):
        user = request.user

        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        try:
            goods = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '商品不存在'})

        try:
             count = int(count)
        except Exception:
            return JsonResponse({'res': 2, 'errmsg': '数量有误'})

        if count <= 0:
            return JsonResponse({'res': 2, 'errmsg': '数量有误'})

        if goods.stock < count:
            return JsonResponse({'res': 3, 'errmsg': '库存不足'})

        # 连接redis
        conn = get_redis_connection('default')
        user_key = 'cart_%s' % user.id
        conn.hset(user_key, sku_id, count)

        return JsonResponse({'res': 9, 'errmsg': '更新完成'})


class CartDeleteView(View):
    """删除数据"""
    def post(self, request):
        user = request.user

        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        sku_id = request.POST.get('sku_id')

        # 校验数据
        try:
            goods = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '商品不存在'})

        # 连接redis
        conn = get_redis_connection('default')
        user_key = 'cart_%s' % user.id
        conn.hdel(user_key, sku_id)
        vals = conn.hvals(user_key)
        count = 0
        for val in vals:
            count += int(val)

        return JsonResponse({'res': 9, 'errmsg': '更新完成', 'count': count})






