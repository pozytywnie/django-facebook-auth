import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django import http
from django.views import generic

import facepy

from facebook_auth import urls


logger = logging.getLogger(__name__)


class Handler(generic.View):
    def get(self, request):
        try:
            self.next_url = urls.Next().decode(request.GET['next'])
        except urls.InvalidNextUrl:
            logger.warning('Invalid facebook handler next.',
                           extra={'request': request})
            return http.HttpResponseBadRequest()
        if 'code' in request.GET:
            try:
                self.login()
            except facepy.FacepyError as e:
                return self.handle_facebook_error(e)
            response = http.HttpResponseRedirect(self.next_url['next'])
            response["P3P"] = ('CP="IDC DSP COR ADM DEVi TAIi PSA PSD IVAi'
                               ' IVDi CONi HIS OUR IND CNT"')
        else:
            response = http.HttpResponseRedirect(self.next_url['close'])
        return response

    def login(self):
        user = authenticate(
            code=self.request.GET['code'],
            redirect_uri=urls.redirect_uri(self.next_url['next'],
                                           self.next_url['close']))
        if user:
            login(self.request, user)

    def handle_facebook_error(self, e):
        return http.HttpResponseRedirect(self.next_url['next'])

handler = Handler.as_view()
