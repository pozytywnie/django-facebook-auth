from django.contrib.auth import models as auth_models
from django.db import models
import facepy
import simplejson

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
        return self.graph.get('me/friends')['data']

    def update_app_friends(self):
        friends = self.friends
        friends_ids = [f['id'] for f in friends]
        self.app_friends.clear()
        self.app_friends.add(*FacebookUser.objects.filter(user_id__in=friends_ids))
