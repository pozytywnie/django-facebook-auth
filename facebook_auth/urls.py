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
from django.core.urlresolvers import reverse


class Next():
    def encode(self, data):
        data = codecs.getencoder('rot-13')(json.dumps(data))[0]
        return urlencode({'next': data})

    def decode(self, data):
        return json.loads(codecs.getdecoder('rot-13')(data)[0])


def redirect_uri(next, close):
    return urljoin(
        settings.FACEBOOK_CANVAS_URL,
        reverse('facebook-auth-handler') + "?" +
        Next().encode({'next': next, 'close': close})
    )

urlpatterns = patterns('facebook_auth.views',
    url(r'^handler$', 'handler', name='facebook-auth-handler'),
)
