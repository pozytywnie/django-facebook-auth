# -*- coding: utf-8 -*-
from functools import wraps
import re
from uuid import uuid1

try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django import http

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_text
from django.utils import html


def get_auth_address(request, redirect_to, scope='', state=None):
    if not state:
        state = force_text(uuid1())
        auth_requests = request.session.get('auth_requests', {})
        if len(auth_requests) >= 20:
            auth_requests = {}
        auth_requests[state] = {
            'method': request.method,
            'POST': request.POST,
            'path': request.path,
            'scope': scope,
        }
        request.session['auth_requests'] = auth_requests
    else:
        scope = (request.session
                 .get('auth_requests', {})
                 .get(state, {})
                 .get('scope', ''))
    args = {
            'client_id': settings.FACEBOOK_APP_ID,
            'redirect_uri': redirect_to,
            'scope': scope,
            'state': state,
    }
    return 'https://www.facebook.com/dialog/oauth?' + urlencode(args)


def use_fallback(get):
    return ('access_denied' == get.get('error', '') and
            'user_denied' == get.get('error_reason', ''))


def accept_login(fallback_template=None, scope=''):
    def decorator(fun):
        @wraps(fun)
        def res(request, *args, **kwargs):
            state = request.GET.get('state', None)
            code = request.GET.get('code', None)
            if state and code:
                old_request = request.session.get('auth_requests', {}).get(
                    state, None)
                if old_request and old_request['path'] == request.path:
                    request.method = old_request['method']
                    request.POST = old_request['POST']
                    del request.session['auth_requests'][state]
                    request.session.modified = True
                    user = authenticate(
                        code=code,
                        redirect_uri=request.build_absolute_uri(request.path))
                    if user:
                        login(request, user)
                if request.method != 'POST':
                    return HttpResponseRedirect(
                        request.build_absolute_uri(request.path))
            if fallback_template and state and use_fallback(request.GET):
                url = get_auth_address(request, request.build_absolute_uri(
                    request.path), state=state)
                return TemplateResponse(request, fallback_template,
                    context={'url': url})
            return fun(request, *args, **kwargs)
        return res
    return decorator


def login_required(scope='', return_view_content=False):
    def decorator(fun):
        @wraps(fun)
        def res(request, *args, **kwargs):
            if request.user.is_authenticated():
                return fun(request, *args, **kwargs)
            else:
                url = get_auth_address(request, request.build_absolute_uri(
                    request.path), scope)
                if return_view_content:
                    response = fun(request, *args, **kwargs)
                else:
                    response = http.HttpResponse(
                        "<html><head><title></title></head><body></body>"
                        "</html>")
                redirect = ("<script>window.top.location=\"%(url)s\";"
                            "</script>" % dict(url=html.escapejs(url)))
                response.content = re.sub(
                    "<body(.*?)>", "<body\\1>" + redirect, response.content)
                return response
        return res
    return decorator
