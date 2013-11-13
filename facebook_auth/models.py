import collections
from datetime import timedelta
import json
import logging
import urllib

try:
    from urllib.parse import parse_qs
except ImportError:
    from urlparse import parse_qs

from celery import task
from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models
from django.utils import timezone
import facepy

from facebook_auth import forms
from facebook_auth import utils

logger = logging.getLogger(__name__)


class FacebookError(Exception):
    pass


class FacebookUser(auth_models.User):
    user_id = models.BigIntegerField(unique=True)
    app_friends = models.ManyToManyField('self')
    scope = models.CharField(max_length=512, blank=True, default='')

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
                .filter(provider_user_id=provider_user_id,
                        deleted=False)
                .latest('expiration_date'))

    @staticmethod
    def invalidate_access_token(token):
        UserToken.objects.filter(token=token).update(deleted=True)


class FacebookTokenManager(object):
    TokenInfo = collections.namedtuple('TokenInfo', ['user', 'expires', 'token'])

    @staticmethod
    def insert_token(access_token, token_expiration_date, user_id):
        token_manager = UserTokenManager()
        if getattr(settings, 'REQUEST_LONG_LIVED_ACCESS_TOKEN', False):
            insert_extended_token.delay(access_token, user_id)
        token_manager.insert_token(user_id, access_token, token_expiration_date)

    def discover_fresh_access_token(self, access_token):
        data = self.debug_token(access_token)
        self.insert_token(access_token, data.expires, data.user)

    @staticmethod
    def convert_expiration_seconds_to_date(seconds):
        return timezone.now() + timedelta(seconds=seconds)

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
            expires_in_seconds = int(parse_qs(data)['expires'][-1])
        except KeyError as e:
            logger.warning('Invalid Facebook response.')
            raise FacebookError
        return access_token, expires_in_seconds

    def debug_token(self, token):
        graph = self._get_application_graph()
        response = graph.get('/debug_token', input_token=token)
        parsed_response = forms.parse_facebook_response(response, token)
        if parsed_response.is_valid:
            data = parsed_response.parsed_data
            self._update_scope(data)
            return self.get_token_info(data)
        else:
            raise ValueError('Invalid Facebook response.', {'errors': parsed_response.errors})

    def _update_scope(self, data):
        if 'scopes' in data:
            (FacebookUser.filter(user_id=data['user_id'])
             .update(scopes=','.join(data['scopes'])))

    def get_token_info(self, response_data):
        return self.TokenInfo(token=response_data['token'],
                              user=response_data['user_id'],
                              expires=response_data['expires_at'])

    @staticmethod
    def _get_application_graph():
        token = facepy.utils.get_application_access_token(settings.FACEBOOK_APP_ID,
                                                          settings.FACEBOOK_APP_SECRET)
        return facepy.GraphAPI(token)


@task()
def validate_token(access_token):
    manager = FacebookTokenManager()
    try:
        manager.debug_token(access_token)
    except ValueError:
        logger.info('Invalid access token')
        token_manager = UserTokenManager()
        token_manager.invalidate_access_token(access_token)


@task()
def insert_extended_token(access_token, user_id):
    manager = FacebookTokenManager()
    token_manager = UserTokenManager()
    try:
        extended_access_token, expires_in_seconds = manager.get_long_lived_access_token(access_token)
    except FacebookError:
        pass
    else:
        token_expiration_date = manager.convert_expiration_seconds_to_date(expires_in_seconds)
        token_manager.insert_token(user_id, extended_access_token, token_expiration_date)
