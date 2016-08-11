import logging

from django.contrib.auth import authenticate
from django.contrib.auth import login
from django import http
from django.views import generic

import facepy

from facebook_auth import utils


logger = logging.getLogger(__name__)


class Handler(generic.View):
    def get(self, request):
        try:
            got_next = self._get_next_from_request(request)
            self.next_url = utils.Next().decode(got_next)
        except utils.InvalidNextUrl:
            logger.warning('Invalid facebook handler next.',
                           extra={'request': request})
            return http.HttpResponseBadRequest()
        if 'code' in request.GET:
            try:
                self.login()
            except facepy.FacepyError as e:
                return self.handle_facebook_error(e)
            response = http.HttpResponseRedirect(self._get_success_url())
            response["P3P"] = ('CP="IDC DSP COR ADM DEVi TAIi PSA PSD IVAi'
                               ' IVDi CONi HIS OUR IND CNT"')
        else:
            response = http.HttpResponseRedirect(self.next_url['close'])
        return response

    def _get_success_url(self):
        return self.next_url['next']

    def _get_next_from_request(self, request):
        if 'next' in request.GET:
            return request.GET['next']
        else:
            raise utils.InvalidNextUrl

    def login(self):
        user = authenticate(
            code=self.request.GET['code'],
            redirect_uri=self._get_redirect_uri())
        if user:
            login(self.request, user)

    def _get_redirect_uri(self):
        return utils.redirect_uri(self.next_url['next'],
                                 self.next_url['close'])

    def handle_facebook_error(self, e):
        return http.HttpResponseRedirect(self.next_url['next'])

handler = Handler.as_view()
