from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings

class FDFSStorage(Storage):
    """fast dfs文件存储"""
    def __init__(self, client_conf=None, storage_url=None):
        if not client_conf:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if not storage_url:
            storage_url = settings.FDFS_STORAGE_URL
        self.storage_url = storage_url

    def _open(self, name, mode='rb'):
        """必须定义文件打开"""
        pass

    def _save(self, name, content):
        """文件保存
        @prama：name 文件名
                content File对象
        """
        client = Fdfs_client(self.client_conf)
        ret = client.upload_by_buffer(content.read())

        if ret.get('Status') != 'Upload successed.':
            raise Exception('文件上传失败')

        filename = ret.get('Remote file_id')

        return filename

    def exists(self, name):
        """Django 判断文件名是否可用"""
        return False

    def url(self, name):
        """读取文件 url属性"""
        return self.storage_url + name


