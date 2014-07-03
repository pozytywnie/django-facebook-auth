import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django import http
from django.views import generic
from facebook_auth import urls


logger = logging.getLogger(__name__)


class Handler(generic.View):
    def get(self, request):
        try:
            next_url = urls.Next().decode(request.GET['next'])
        except urls.InvalidNextUrl:
            logger.warning('Invalid facebook handler next.',
                           extra={'request': request})
            return http.HttpResponseBadRequest()
        if 'code' not in request.GET:
            return http.HttpResponseRedirect(next_url['close'])
        user = authenticate(
            code=request.GET['code'],
            redirect_uri=urls.redirect_uri(next_url['next'],
                                           next_url['close']))
        if user:
            login(request, user)
        response = http.HttpResponseRedirect(next_url['next'])
        response["P3P"] = ('CP="IDC DSP COR ADM DEVi TAIi PSA PSD IVAi IVDi'
                           ' CONi HIS OUR IND CNT"')
        return response

handler = Handler.as_view()
