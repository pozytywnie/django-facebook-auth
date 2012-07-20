# -*- coding: utf-8 -*-
from functools import wraps
import urllib
from uuid import uuid1

from django import http
from django.conf import settings

from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.utils import html

def get_auth_address(request, redirect_to, scope=''):
    state = unicode(uuid1())
    auth_requests = request.session.get('auth_requests', {})
    if len(auth_requests) >= 20:
        auth_requests = {}
    auth_requests[state] = {
        'method': request.method,
        'POST': request.POST,
        'path': request.path,
    }
    request.session['auth_requests'] = auth_requests
    args = {
            'client_id': settings.FACEBOOK_APP_ID,
            'redirect_uri': redirect_to,
            'scope': scope,
            'state': state,
    }
    return 'https://www.facebook.com/dialog/oauth?' + urllib.urlencode(args)


def accept_login():
    def decorator(fun):
        @wraps(fun)
        def res(request, *args, **kwargs):
            state = request.GET.get('state', None)
            code = request.GET.get('code', None)
            if state and code:
                old_request = request.session.get('auth_requests', {}).get(state, None)
                if old_request and old_request['path'] == request.path:
                    request.method = old_request['method']
                    request.POST = old_request['POST']
                    del request.session['auth_requests'][state]
                    request.session.modified = True
                    user = authenticate(code=code, redirect_uri=request.build_absolute_uri(request.path))
                    if user:
                        login(request, user)
                if request.method != 'POST':
                    return HttpResponseRedirect(request.build_absolute_uri(request.path))
            return fun(request, *args, **kwargs)
        return res
    return decorator


def login_required(scope=''):
    def decorator(fun):
        @wraps(fun)
        def res(request, *args, **kwargs):
            if request.user.is_authenticated():
                return fun(request, *args, **kwargs)
            else:
                url = get_auth_address(request, request.build_absolute_uri(request.path), scope)
                return http.HttpResponse(("<html><head><title></title></head>"
                        "<body><script>window.top.location=\"%(url)s\";</script></body>"
                        "</html>") % dict(url=html.escapejs(url)))
        return res
    return decorator
