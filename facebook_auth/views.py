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
        if 'code' in request.GET:
            self.login(next_url)
            response = http.HttpResponseRedirect(next_url['next'])
            response["P3P"] = ('CP="IDC DSP COR ADM DEVi TAIi PSA PSD IVAi'
                               ' IVDi CONi HIS OUR IND CNT"')
        else:
            response = http.HttpResponseRedirect(next_url['close'])
        return response

    def login(self, next_url):
        user = authenticate(
            code=self.request.GET['code'],
            redirect_uri=urls.redirect_uri(next_url['next'],
                                           next_url['close']))
        if user:
            login(self.request, user)

handler = Handler.as_view()
