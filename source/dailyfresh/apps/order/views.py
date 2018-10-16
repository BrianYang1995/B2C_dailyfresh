from django.shortcuts import render, HttpResponse, redirect
from django.views.generic import View
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings

from utils.mixin import LoginRequestMixIn
from goods.models import GoodsSKU
from user.models import Address
from order.models import OrderInfo, OrderGoods

from django_redis import get_redis_connection
from datetime import datetime
from alipay import AliPay
import os
import time


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

        goods_ids = []
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
        goods_str = ','.join(goods_skus)
        context = {
            'goods_list': goods_list,
            'count': count,
            'amount_price': amount_price,
            'transite_price': transite_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'goods_str': goods_str,
        }
        return render(request, 'place_order.html', context)


class OrderCommitView(View):
    """处理用户提交订单"""
    @transaction.atomic
    def post(self, request):
        # todo: 用户认证
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # todo: 接收参数
        addr_id = request.POST.get('addr_id')  # 收货地址id
        pay_style = request.POST.get('pay_style_id')  # 支付方式id
        sku_ids = request.POST.get('sku_ids')  # 商品id字符串

        # todo: 校验参数
        if not all([addr_id, pay_style, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '信息不全'})

        # 支付方式
        if pay_style not in OrderInfo.PAY_METHOD:
            return JsonResponse({'res': 2, 'errmsg': '支付方式有误'})

        # 收货地址
        try:
            addr = Address.objects.filter(user_id=user.id, id=addr_id)[0]
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '收货地址有误'})

        # 连接redis获取购物车数据
        conn = get_redis_connection('default')
        user_key = 'cart_%s' % user.id

        sku_ids = sku_ids.split(',')

        total_count = 0
        total_price = 0
        goods_list = []
        # 商品校验
        save_id = transaction.savepoint()

        try:
            for sku_id in sku_ids:
                for i in range(0, 3):
                    try:
                        goods = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                    count = conn.hget(user_key, sku_id)
                    if not count:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '购物车数据有误'})

                    if goods.stock < int(count):
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '库存不足'})

                    goods.count = count
                    goods_list.append(goods)

                    ##
                    # print(user, ':', goods.stock)

                    orign_stock = goods.stock
                    new_stock = goods.stock - int(count)
                    new_sales = goods.stock + int(count)
                    # 乐观锁
                    res = GoodsSKU.objects.filter(id=goods.id, stock=orign_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        if i == 2:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 8, 'errmsg': '数量有限，下次再来'})
                        continue

                    # todo: 计算总数目，总价
                    total_count += int(count)
                    total_price += int(count) * int(goods.price)
                    break

                data_str = datetime.now().strftime('%Y%m%d%H%M%s')
                order_id = data_str + str(user.id)

                # todo: 生成订单信息
                order_info = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    addr=addr,
                    pay_method=int(pay_style),
                    total_count=total_count,
                    total_price=total_price,
                    transit_price=12
                )

                # todo: 添加订单商品
                for goods in goods_list:
                    OrderGoods.objects.create(
                        order=order_info,
                        sku_id=goods.id,
                        count=goods.count,
                        price=goods.price
                    )

        except Exception as e:
            transaction.savepoint_rollback(save_id)

            return JsonResponse({'res': 5, 'errmsg': '下单失败'})

        transaction.savepoint_commit(save_id)

        conn.hdel(user_key, *sku_ids)
        # print(user, "下单成功")
        return JsonResponse({'res': 9, 'errmsg': '下单成功'})


class OrderPayView(View):
    def post(self, request):
        """用户支付"""
        # todo: 用户验证
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # todo: 获取订单id
        order_id = request.POST.get('order_id')

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '订单信息有误'})

        # todo: 支付宝提交订单，返回用户支付页面
        # 初始化支付宝
        app_private_key_addr = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        alipay_public_key_addr = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')

        app_private_key_string = open(app_private_key_addr).read()
        alipay_public_key_string = open(alipay_public_key_addr).read()

        alipay = AliPay(
            appid = "2016092100560492",  # 应用id
            app_notify_url = None,  # 默认回调url
            # app私钥

            app_private_key_string = app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string = alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True,  # 默认False
        )

        # 电脑网站支付
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(order.total_price + order.transit_price),
            subject='天天生鲜 order_id: %s' % order_id,
            return_url=None,  # 同步返回地址
            notify_url=None  # 异步返回地址
        )

        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        # todo: 返回支付页面
        return JsonResponse({'res': 9, 'pay_url': pay_url})


class OrderCheckView(View):
    def post(self, request):
        """查询订单结果"""

        # todo: 用户验证
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # todo: 获取订单id
        order_id = request.POST.get('order_id')

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '订单信息有误'})

        # todo: 初始化支付宝
        app_private_key_addr = os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')
        alipay_public_key_addr = os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')

        app_private_key_string = open(app_private_key_addr).read()
        alipay_public_key_string = open(alipay_public_key_addr).read()

        alipay = AliPay(
            appid = "2016092100560492",  # 应用id
            app_notify_url = None,  # 默认回调url
            # app私钥

            app_private_key_string = app_private_key_string,
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string = alipay_public_key_string,
            sign_type="RSA2",  # RSA 或者 RSA2
            debug = True,  # 默认False
        )

        # todo: 查询订单
        while True:
            result = alipay.api_alipay_trade_query(out_trade_no=order_id)

            if result['code'] == '10000' and result['trade_status'] == 'TRADE_SUCCESS':
                order.order_status = 4
                order.trade_no = result['trade_no']
                order.save()

                return JsonResponse({'res': 9, 'errmsg': '支付成功'})
            elif result['code'] == '20000' or result['code'] == '40004' or (result['code'] == '10000' and result['trade_status'] == 'WAIT_BUYER_PAY'):
                time.sleep(5)
                continue
            else:
                return JsonResponse({'res': 4, 'errmsg': '交易失败'})


class CommentView(LoginRequestMixIn, View):
    """订单评论"""
    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user

        # 校验数据
        if not order_id:
            return redirect('user:order')

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect("user:order")

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count*order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        # 校验数据
        if not order_id:
            return redirect('user:order')

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect("user:order")

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i) # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '') # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            print(content)
            order_goods.comment = content
            order_goods.save()

        order.order_status = 5 # 已完成
        order.save()

        return redirect("user:order", 1)











