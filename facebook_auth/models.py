import json
import logging

from django.contrib.auth import models as auth_models
from django.db import models
from django.utils import timezone
import facepy

from facebook_auth import utils

logger = logging.getLogger(__name__)


class FacebookUser(auth_models.User):
    user_id = models.BigIntegerField(unique=True)
    access_token = models.TextField(blank=True, null=True)
    access_token_expiration_date = models.DateTimeField(blank=True, null=True)
    app_friends = models.ManyToManyField('self')

    @property
    def graph(self):
        return facepy.GraphAPI(self.access_token)

    @property
    def js_session(self):
        return json.dumps({
            'access_token': self.access_token,
            'uid': self.user_id
        })

    @property
    def friends(self):
        response = utils.get_from_graph_api(self.graph, "me/friends")
        if 'data' in response:
            return response['data']
        logger.warning("OpenGraph error: %s" % response)
        return []

    def update_app_friends(self):
        friends = self.friends
        friends_ids = [f['id'] for f in friends]
        existing_friends = self.app_friends.all().values_list('user_id', flat=True)
        new_friends = FacebookUser.objects.filter(user_id__in=friends_ids).exclude(user_id__in=existing_friends)
        removed_friends = self.app_friends.exclude(user_id__in=friends_ids)
        self.app_friends.add(*new_friends)
        self.app_friends.remove(*removed_friends)


class UserToken(models.Model):
    provider_user_id = models.CharField(max_length=255)
    token = models.TextField()
    expiration_date = models.DateTimeField(blank=True, null=True)
    deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User token'
        verbose_name_plural = 'User tokens'


class UserTokenManager(object):
    @staticmethod
    def insert_token(provider_user_id, token, expiration_date):
        UserToken.objects.get_or_create(provider_user_id=provider_user_id,
                                        token=token,
                                        expiration_date=expiration_date)

    @staticmethod
    def get_access_token(provider_user_id):
        now = timezone.now()
        return (UserToken.objects
                .filter(provider_user_id=provider_user_id,
                        expiration_date__gt=now)
                .latest('expiration_date'))

    @staticmethod
    def invalidate_access_token(token):
        UserToken.objects.filter(token=token).update(deleted=True)
