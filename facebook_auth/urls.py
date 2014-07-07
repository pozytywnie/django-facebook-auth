import json
try:
    from urllib.parse import urljoin
    from urllib.parse import urlencode
except ImportError:
    from urlparse import urljoin
    from urllib import urlencode

from django.conf import settings
from django.conf.urls import patterns
from django.conf.urls import url
from django.core import signing
from django.core.urlresolvers import reverse
from django.utils import encoding


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

urlpatterns = patterns('facebook_auth.views',
    url(r'^handler$', 'handler', name='facebook-auth-handler'),
)
