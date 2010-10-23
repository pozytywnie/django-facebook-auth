from django import http
from django.contrib.auth import authenticate, login
from facebook_auth import urls

def handler(request):
    next = urls.Next().decode(request.GET['next'])
    if 'code' not in request.GET:
        return http.HttpResponseRedirect(next['close'])
    user = authenticate(code=request.GET['code'],
                        redirect_uri=urls.redirect_uri(next['next'], next['close']))
    if user:
        login(request, user)
    return http.HttpResponseRedirect(next['next'])
