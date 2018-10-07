from django.shortcuts import render

# Create your views here.

def index(request):
    """返回主页面"""

    return render(request, 'index.html')
