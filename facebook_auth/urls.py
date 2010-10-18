import codecs
import simplejson
import urllib
import urlparse

from django.conf.urls.defaults import patterns, url
from django.conf import settings
from django.core.urlresolvers import reverse

class Next():
    def encode(self, data):
        data = codecs.getencoder('rot13')(simplejson.dumps(data))[0]
        return urllib.urlencode({'next': data})

    def decode(self, data):
        return simplejson.loads(codecs.getdecoder('rot13')(data)[0])

def redirect_uri(next):
    return urlparse.urljoin(
        settings.FACEBOOK_CANVAS_URL,
        reverse('facebook-auth-handler') + "?" +
        Next().encode({'next': next})
    )

urlpatterns = patterns('facebook_auth.views',
    url(r'^handler$', 'handler', name='facebook-auth-handler'),
)
