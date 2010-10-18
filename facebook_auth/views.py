from django import http
from django.contrib.auth import authenticate, login
from facebook_auth import urls

def handler(request):
    next = urls.Next().decode(request.GET['next'])['next']
    user = authenticate(code=request.GET['code'], redirect_uri=urls.redirect_uri(next))
    if user:
        login(request, user)
    return http.HttpResponseRedirect(next)
