from django.contrib.auth.decorators import login_required


class LoginRequestMixIn(object):

    @classmethod
    def as_view(cls, **initkwargs):
        """view类"""
        view = super(LoginRequestMixIn, cls).as_view(**initkwargs)
        return login_required(view)