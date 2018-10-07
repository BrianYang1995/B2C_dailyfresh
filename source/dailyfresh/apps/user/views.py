from django.shortcuts import render, redirect, HttpResponse
from django.views.generic import View
from django.conf import settings
from django.contrib.auth import authenticate, login, logout

from user.models import User
from celery_task.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
import re


class RegisterView(View):
    '''用户注册'''
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
            response = redirect('goods:index')
            remember = request.POST.get('remember')
            if remember == 'on':
                response.set_cookie('username', username)
            else:
                response.delete_cookie('username')
            return response









