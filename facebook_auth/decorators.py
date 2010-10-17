# -*- coding: utf-8 -*-
import urllib
import urlparse

from django import http
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.utils.datastructures import MultiValueDictKeyError
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

def _has_code(get, session):
    res = 'code' in get and TICKET_VAR in session
    if res:
        del session[TICKET_VAR]
    return res

def login_required(close='http://www.facebook.com', force=False, extended=[]):
    def decorator(fun):
        def res(request, *args, **kwargs):
            if request.user.is_authenticated() and (not force or _check_logined(request.user.access_token)):
                return _allow(request, lambda: fun(request, *args, **kwargs))
            else:
                next = urlparse.urljoin(settings.FACEBOOK_APP_URL, request.path[1:])
                if 'error_reason' in request.GET:
                    return http.HttpResponse('<script>window.top.location="%s"</script>' % close)

                if _has_code(request.GET, request.session):
                    code_redirect_uri = next
                    user = authenticate(code=request.GET['code'], redirect_uri=code_redirect_uri)
                    if user is not None:
                        if user.is_active:
                            login(request, user)
                            return _allow(request, lambda: fun(request, *args, **kwargs))
                        else:
                            return http.HttpResponse('account not active')

                url_base = 'https://graph.facebook.com/oauth/authorize?'
                redirect_uri = next
                args = {
                    'type': 'client_cred',
                    'client_id': settings.FACEBOOK_APP_ID,
                    'redirect_uri': redirect_uri,
                }
                if extended:
                    args['scope'] = ','.join(extended)
                url =  url_base + urllib.urlencode(args)
                request.session[TICKET_VAR] = True
                return http.HttpResponse('<script>document.cookie="%s=%s";window.top.location="%s";</script>'%(settings.SESSION_COOKIE_NAME, request.session.session_key, url))
        return res
    return decorator

