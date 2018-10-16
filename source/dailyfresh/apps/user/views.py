from django.shortcuts import render, redirect, HttpResponse
from django.views.generic import View
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator


from celery_task.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
import re
from django_redis import get_redis_connection

from utils.mixin import LoginRequestMixIn
from user.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo
from order.models import OrderGoods



class RegisterView(View):
    """用户注册"""
    def get(self, request):
        """返回注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """处理用户注册信息"""
        # 接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')
        cpassword = request.POST.get('cpassword')
        email = request.POST.get('email')

        # 校验参数
        # 数据完整性
        if not all([username, password, cpassword, email]):
            return render(request, 'register.html', {'errmsg': '请填写完整信息'})
        # 密码是否相同
        if password != cpassword:
            return render(request, 'register.html', {'errmsg': '两次密码不相同'})
        # 验证邮箱格式
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 用户名是否存在
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = None

        if user:
            return render(request, 'register.html', {'errmsg': '用户已存在'})

        # 是否同意协议
        allow = request.POST.get('allow')
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意相关协议'})

        # 业务逻辑处理
        # 保存用户
        try:
            user = User.objects.create_user(username, email, password)
            user.is_active = 0
            user.save()
        except Exception as e:
            return render(request, 'register.html', {'errmsg': '创建用户失败'})

        # 发送用户激活邮件
        # 生成token
        serializer = Serializer(settings.SECRET_KEY, 3600)
        token = serializer.dumps({'confirm': user.id})
        token = token.decode()

        # 发送邮件：使用celery任务队列
        send_register_active_email.delay(email, user.username, token)

        return redirect('goods:index')


class ActiveView(View):
    """用户激活"""
    def get(self, request, token):
        """获取激活连接"""
        # 创建itsdangerous实例
        serializer = Serializer(settings.SECRET_KEY, 3600)

        # 数据库中查询的用户
        try:
            # 获取token
            info = serializer.loads(token)
            user_id = info['confirm']
            # 激活用户
            user = User.objects.get(pk=user_id)
            user.is_active = 1
            user.save()
            return HttpResponse('验证成功')
        except SignatureExpired:
            return HttpResponse('验证连接过期')


class LoginView(View):
    """用户登录"""
    def get(self, request):
        """返回登录页面"""
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        """用户登录处理"""
        # 接收参数
        username = request.POST.get('username')
        password = request.POST.get('password')

        # 校验参数
        # 完整性
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '请将数据填写完整'})

        # 验证用户名和密码
        user = authenticate(username=username, password=password)

        if user is None:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})

        else:
            login(request, user)
            next_page = request.GET.get('next', 'goods:index')
            response = redirect(next_page)
            remember = request.POST.get('remember')
            if remember == 'on':
                response.set_cookie('username', username)
            else:
                response.delete_cookie('username')
            return response


class LogoutView(View):
    """登出"""
    def get(self, request):
        """用户登出"""
        logout(request)
        return redirect('goods:index')


class UserAddressView(LoginRequestMixIn, View):
    """用户中心收货地址"""
    def get(self, request):
        # 获取默认收货地址
        user = request.user
        addr = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page': 'address', 'addr': addr})

    def post(self, request):
        """用户收获地址提交"""
        # 接收数据
        receiver = request.POST.get('receiver')
        address = request.POST.get('address')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        # 验证数据完整性
        if not all([receiver, address, zip_code, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '提交收件人信息不完整'})

        # 验证手机号
        if not re.match('^1[34578][0-9]{9}', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机号有误'})

        # 保存数据
        user = request.user

        # 判断用户是否有默认地址
        addr = Address.objects.get_default_address(user)

        if addr:
            is_default = False
        else:
            is_default = True
        # 保存用户地址
        try:
            addr = Address.objects.create(
                user=user,
                receiver=receiver,
                addr=address,
                zip_code=zip_code,
                phone=phone,
                is_default=is_default
            )
        except Exception:
            return render(request, 'user_center_site.html', {'errmsg': '保存数据库失败'})

        return redirect('user:address')


class UserOrderView(LoginRequestMixIn, View):
    """用户中心订单"""
    def get(self, request, page):
        # todo: 获取用户信息
        user = request.user
        # todo: 获取订单数据
        try:
            orders = OrderInfo.objects.filter(user=user).all().order_by('-create_date')
        except OrderInfo.DoesNotExist:
            orders = None

        # todo: 循环获取订单商品
        for order in orders:
            try:
                goods_list = OrderGoods.objects.filter(order=order).all()
            except OrderGoods.DoesNotExist:
                goods_list = None

            order.goods_list = goods_list
            order.status = OrderInfo.ORDER_STATUS[order.order_status]

            # todo: 商品小计
            if goods_list:
                for goods in goods_list:
                    price = float(goods.price)
                    count = int(goods.count)

                    goods.total_price = price * count

        paginator = Paginator(orders, 2)

        try:
            page = int(page)
        except Exception:
            page = 1

        if page > paginator.num_pages:
            page = 1

        num_pages = paginator.num_pages
        if num_pages < 5:
            page_list = range(1, num_pages + 1)
        elif page <= 3:
            page_list = range(1, 6)
        elif page >= num_pages - 3:
            page_list = range(num_pages - 4, num_pages + 1)
        else:
            page_list = range(page - 2, page + 3)

        page = paginator.page(page)
        print(page)

        # todo: 整理上下文
        context = {
            'orders': page,
            'page': 'order',
            'page_list': page_list,
        }

        return render(request, 'user_center_order.html', context)


class UserBaseInfoView(LoginRequestMixIn, View):
    """用户中心基本信息"""
    def get(self, request):
        # 获取用户信息
        user = request.user
        try:
            addr = Address.objects.get(user_id=user.id, is_default=True)
        except Address.DoesNotExist:
            addr = None

        redis_conn = get_redis_connection('default')
        sku_ids = redis_conn.lrange('history_%s' % user.id, 0, 4)

        goods_list = []
        for id in sku_ids:
            try:
                goods = GoodsSKU.objects.get(id=id)
            except GoodsSKU.DoesNotExist:
                pass
            goods_list.append(goods)

        return render(request, 'user_center_info.html', {'page': 'info', 'user_info': addr, 'goods_list': goods_list})
