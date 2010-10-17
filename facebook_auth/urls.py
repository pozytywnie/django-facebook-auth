import codecs
import simplejson
import urllib

class Next():
    def encode(self, data):
        data = codecs.getencoder('rot13')(simplejson.dumps(data))[0]
        return urllib.urlencode({'next': data})

    def decode(self, data):
        return simplejson.loads(codecs.getdecoder('rot13')(data)[0])

