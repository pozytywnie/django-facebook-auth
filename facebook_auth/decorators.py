# -*- coding: utf-8 -*-
from functools import wraps
import urllib
import urlparse
import urls

from django import http
from django.conf import settings
from facebook import GraphAPI, GraphAPIError


TICKET_VAR = 'facebook_auth_ticket'

def _check_logined(access_token):
    try:
        GraphAPI(access_token).get_object('me')
        return True
    except GraphAPIError:
        return False

def _allow(request, fun):
    if hasattr(settings, 'FACEBOOK_ALLOW_UIDS'):
        if request.user.user_id not in settings.FACEBOOK_ALLOW_UIDS:
            return http.HttpResponse('Brak dostępu. Skontaktuj się z administratorem.')
    return fun()

def login_required(close='http://www.facebook.com', force=False, extended=[]):
    def decorator(fun):
        @wraps(fun)
        def res(request, *args, **kwargs):
            if request.user.is_authenticated() and (not force or _check_logined(request.user.access_token)):
                return _allow(request, lambda: fun(request, *args, **kwargs))
            else:
                next = urlparse.urljoin(settings.FACEBOOK_APP_URL, request.path[1:])
                url_base = 'https://graph.facebook.com/oauth/authorize?'
                redirect_uri = urls.redirect_uri(next, close)
                args = {
                    'type': 'client_cred',
                    'client_id': settings.FACEBOOK_APP_ID,
                    'redirect_uri': redirect_uri,
                }
                if extended:
                    args['scope'] = ','.join(extended)
                url =  url_base + urllib.urlencode(args)
                return http.HttpResponse('<script>window.top.location="%s";</script>' % url)
        return res
    return decorator
