from django.shortcuts import render, redirect
from django.views.generic import View
from django.core.cache import cache
from django.core.paginator import Paginator

from goods.models import (
    GoodsType, GoodsSKU, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, Goods
)
from order.models import OrderGoods

import django_redis


class IndexView(View):
    """主页显示"""
    def get(self, request):
        """渲染主页"""
        # 从缓存中读取数据
        context = cache.get('static_index_data')

        if not context:
            print('写入缓存')
            # 商品分类
            try:
                types = GoodsType.objects.all()
            except Exception:
                pass

            # 轮播图
            try:
                goods_banner = IndexGoodsBanner.objects.all().order_by('index')[:4]
            except Exception:
                pass

            # 促销活动
            try:
                promotion = IndexPromotionBanner.objects.all().order_by('index')[:2]
            except Exception:
                pass

            # 商品列表
            for type in types:
                try:
                    text_goods_list = IndexTypeGoodsBanner.objects.filter(display_type=0, type=type).order_by('index').all()[:3]
                    image_goods_list = IndexTypeGoodsBanner.objects.filter(display_type=1, type=type).order_by('index').all()[:4]
                    type.text_goods_list = text_goods_list
                    type.image_goods_list = image_goods_list
                except Exception:
                    pass

            context = {
                'types': types,
                'goods_banner': goods_banner,
                'promotion': promotion,
            }
            cache.set('static_index_data', context, 3600)

        # 购物车数据
        cart_count = 0
        user = request.user
        if user.is_authenticated:
            conn = django_redis.get_redis_connection('default')
            key = 'cart_%s' % user.id
            cart_count = conn.hlen(key)

        # 上下文处理
        context.update(cart_count=cart_count)

        return render(request, 'index.html', context)


class DetailView(View):
    """产品详情页"""
    def get(self, request, goods_id):
        """获取产品详情"""
        # 校验数据
        try:
            goods_id = int(goods_id)
        except Exception:
            return redirect('goods:index')

        try:
            goods = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect('goods:index')

        # 获取同类spu信息
        try:
            goods_list = GoodsSKU.objects.filter(goods=goods.goods).exclude(id=goods.id)
        except Exception:
            goods_list = None

        # 获取所有种类信息
        types = cache.get('goods_types')
        if not types:
            types = GoodsType.objects.all()
            cache.set('goods_types', types, 3600)

        # 获取评论信息
        try:
            order_goods = OrderGoods.objects.filter(sku=goods).exclude(commit='')
        except OrderGoods.DoesNotExist:
            order_goods = None

        # 新品推荐
        try:
            new_goods = GoodsSKU.objects.filter(type=goods.type).order_by('-create_date')[:2]
        except Exception:
            new_goods = None

        # 购物车
        cart_count = 0
        user = request.user
        if user.is_authenticated:
            conn = django_redis.get_redis_connection('default')
            key = 'cart_%s' % user.id
            cart_count = conn.hlen(key)
            history_key = 'history_%s'% user.id
            conn.lrem(history_key, 0, goods_id)
            conn.lpush(history_key, goods.id)
            conn.ltrim(history_key, 0, 4)

        # 整理上下文
        context = {
            'types': types,
            'goods': goods,
            'order_goods': order_goods,
            'new_goods': new_goods,
            'cart_count': cart_count,
            'goods_list': goods_list,
        }
        return render(request, 'detail.html', context)


class ListView(View):
    """产品列表页"""
    def get(self, request, type_id, page):
        """返回对应种类产品列表"""
        # 校验数据
        try:
            type_id = int(type_id)
        except Exception:
            return redirect('goods:index')

        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect('goods:index')
        # 查询
        # 排序方式
        sort = request.GET.get('sort')
        if sort == 'hot':
            order_by_type = '-sales'
        elif sort == 'price':
            order_by_type = 'price'
        else:
            order_by_type = 'id'
            sort = 'default'
        try:
            goods_list = GoodsSKU.objects.filter(type=type).order_by(order_by_type)
        except GoodsSKU.DoesNotExist:
            return redirect('goods:index')

        # 分页信息
        paginator = Paginator(goods_list, 1)
        try:
            page = int(page)
        except Exception:
            page = 1
        if page > paginator.num_pages:
            page = 1

        num_pages = paginator.num_pages
        if num_pages < 5:
            page_list = range(1, num_pages+1)
        elif page <= 3:
            page_list = range(1, 6)
        elif page >= num_pages-3:
            page_list = range(num_pages-4, num_pages+1)
        else:
            page_list = range(page-2, page+3)

        page = paginator.page(page)

        # 获取所有种类信息
        types = cache.get('goods_types')
        if not types:
            print('设置商品种类缓存')
            types = GoodsType.objects.all()
            cache.set('goods_types', types, 3600)

        # 新品推荐
        try:
            new_goods = GoodsSKU.objects.filter(type=type).order_by('-create_date')[:2]
        except Exception:
            new_goods = None

        # 购物车
        cart_count = 0
        user = request.user
        if user.is_authenticated:
            conn = django_redis.get_redis_connection('default')
            key = 'cart_%s' % user.id
            cart_count = conn.hlen(key)

        # 整理上下文
        context = {
            'type': type,
            'new_goods': new_goods,
            'page': page,
            'types': types,
            'sort': sort,
            'cart_count': cart_count,
            'page_list': page_list
        }

        return render(request, 'list.html', context)









