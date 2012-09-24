from django.contrib.auth import models as auth_models
from django.db import models
from django.utils import simplejson
import facepy

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
        if len(FacebookUser.objects.filter(pk=self.pk).select_for_update()):
            friends = self.friends
            friends_ids = [f['id'] for f in friends]
            self.app_friends = FacebookUser.objects.filter(user_id__in=friends_ids)
