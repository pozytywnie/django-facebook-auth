from uuid import uuid1

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models
import facepy
import simplejson

from facebook_auth import utils

class FacebookUser(auth_models.User):
    user_id = models.BigIntegerField(unique=True)
    access_token = models.TextField(blank=True, null=True)
    app_friends = models.ManyToManyField('self')

    @property
    def graph(self):
        return facepy.GraphAPI(self.access_token)

    @property
    def js_session(self):
        return simplejson.dumps({
            'access_token': self.access_token,
            'uid': self.user_id
        })

    @property
    def friends(self):
        return utils.get_from_graph_api(self.graph, "me/friends")['data']

    def update_app_friends(self):
        friends = self.friends
        friends_ids = [f['id'] for f in friends]
        self.app_friends.clear()
        self.app_friends.add(*FacebookUser.objects.filter(user_id__in=friends_ids))


def get_auth_address(request, redirect_to, scope=''):
    state = unicode(uuid1())
    request.session['state'] = state
    return 'https://www.facebook.com/dialog/oauth?client_id=%s&redirect_uri=%s&scope=%s&state=%s' % (
        settings.FACEBOOK_APP_ID, redirect_to, scope, state
    )
