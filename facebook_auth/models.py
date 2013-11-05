import json
import logging
import urllib

try:
    from urllib.parse import parse_qs
except ImportError:
    from urlparse import parse_qs

from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models
import facepy

from facebook_auth import utils

logger = logging.getLogger(__name__)


class FacebookUser(auth_models.User):
    user_id = models.BigIntegerField(unique=True)
    app_friends = models.ManyToManyField('self')

    @property
    def access_token(self):
        try:
            return self._get_token_object().token
        except UserToken.DoesNotExist:
            return None

    @property
    def access_token_expiration_date(self):
        return self._get_token_object().expiration_date

    def _get_token_object(self):
        return UserTokenManager.get_access_token(self.user_id)

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
        return (UserToken.objects
                .filter(provider_user_id=provider_user_id)
                .latest('expiration_date'))

    @staticmethod
    def invalidate_access_token(token):
        UserToken.objects.filter(token=token).update(deleted=True)

    @staticmethod
    def get_long_lived_access_token(access_token):
        url_base = 'https://graph.facebook.com/oauth/access_token?'
        args = {
            'client_id': settings.FACEBOOK_APP_ID,
            'client_secret': settings.FACEBOOK_APP_SECRET,
            'grant_type': 'fb_exchange_token',
            'fb_exchange_token': access_token,
        }
        data = urllib.urlopen(url_base + urllib.urlencode(args)).read()
        try:
            access_token = parse_qs(data)['access_token'][-1]
        except KeyError:
            pass
        return access_token
