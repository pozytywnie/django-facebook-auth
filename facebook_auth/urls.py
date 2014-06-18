import codecs
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

class InvalidNextUrl(Exception):
    pass

class Next():
    salt = 'facebook_auth.urls.Next'

    def encode(self, data):
        data = signing.dumps(data, salt=self.salt)
        return urlencode({'next': data})

    def decode(self, data):
        try:
            return signing.loads(data, salt=self.salt)
        except signing.BadSignature:
            raise InvalidNextUrl()


def redirect_uri(next, close):
    return urljoin(
        settings.FACEBOOK_CANVAS_URL,
        reverse('facebook-auth-handler') + "?" +
        Next().encode({'next': next, 'close': close})
    )

urlpatterns = patterns('facebook_auth.views',
    url(r'^handler$', 'handler', name='facebook-auth-handler'),
)
