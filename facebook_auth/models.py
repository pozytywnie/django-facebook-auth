from django.contrib.auth import models
from django.db.models import fields
import facebook
import simplejson
from django.conf import settings

class FacebookUser(models.User):
    user_id = fields.BigIntegerField(unique=True)
    access_token = fields.TextField(blank=True, null=True)

    @property
    def graph(self):
        return facebook.GraphAPI(self.access_token)

    @property
    def js_session(self):
        return simplejson.dumps({
            'access_token': self.access_token,
            'uid': self.user_id
        })

    @property
    def friends(self):
        return self.graph.get_connections('me', 'friends')['data']

