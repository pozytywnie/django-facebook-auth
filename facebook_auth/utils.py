import json
try:
    from urllib.parse import urljoin
    from urllib.parse import urlencode
except ImportError:
    from urlparse import urljoin
    from urllib import urlencode

import facepy
from django.conf import settings
from django.utils import timezone

from django.conf import settings
from django.core import signing
from django.core.urlresolvers import reverse
from django.utils import encoding

from . facepy_wrapper import utils

GRAPH_MAX_TRIES = 3
FACEBOOK_TIMEOUT = getattr(settings, 'FACEBOOK_AUTH_BACKEND_FACEBOOK_TIMEOUT',
                           timezone.timedelta(seconds=20).total_seconds())
FACEBOOK_API_VERSION = getattr(settings, 'FACEBOOK_API_VERSION', '2.1')

class InvalidNextUrl(Exception):
    pass


class Next(object):
    salt = 'facebook_auth.urls.Next'

    def encode(self, data):
        data = self.dumps(data)
        return urlencode({'next': data})

    def decode(self, data):
        try:
            return self.loads(data)
        except signing.BadSignature:
            raise InvalidNextUrl()

    def dumps(self, obj):
        data = json.dumps(
            obj, separators=(',', ':'), sort_keys=True).encode('utf-8')
        base64d = signing.b64_encode(data)
        return signing.Signer(salt=self.salt).sign(base64d)

    def loads(self, s):
        base64d = encoding.force_bytes(
            signing.Signer(salt=self.salt).unsign(s))
        data = signing.b64_decode(base64d)
        return json.loads(data.decode('utf-8'))


def redirect_uri(next, close):
    return urljoin(
        settings.FACEBOOK_CANVAS_URL,
        reverse('facebook-auth-handler') + "?" +
        Next().encode({'next': next, 'close': close})
    )


def get_from_graph_api(graphAPI, query):
    for i in range(GRAPH_MAX_TRIES):
        try:
            return graphAPI.get(query)
        except facepy.FacepyError as e:
            if i == GRAPH_MAX_TRIES - 1 or getattr(e, 'code', None) != 1:
                raise


def get_application_graph(version=None):
    version = version or FACEBOOK_API_VERSION
    token = (facepy.utils
             .get_application_access_token(settings.FACEBOOK_APP_ID,
                                           settings.FACEBOOK_APP_SECRET,
                                           api_version=version))
    return get_graph(token)


def get_graph(*args, **kwargs):
    version = FACEBOOK_API_VERSION
    return utils.get_graph(*args, version=version, timeout=FACEBOOK_TIMEOUT, **kwargs)


def get_long_lived_access_token(access_token):
    return utils.get_long_lived_access_token(
        access_token=access_token,
        client_id=settings.FACEBOOK_APP_ID,
        client_secret=settings.FACEBOOK_APP_SECRET,
    )


def get_access_token(code=None, redirect_uri=None):
    return utils.get_access_token(
        code=code,
        redirect_uri=redirect_uri,
        client_id=settings.FACEBOOK_APP_ID,
        client_secret=settings.FACEBOOK_APP_SECRET,
        timeout=FACEBOOK_TIMEOUT,
    )
