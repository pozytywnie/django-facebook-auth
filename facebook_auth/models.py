import collections
from datetime import timedelta
import json
import logging

try:
    from urllib.error import HTTPError
    import urllib.parse as urlparse
except ImportError:
    import urlparse
    from urllib2 import HTTPError


from django.conf import settings
from django.contrib.auth import models as auth_models
from django.db import models
from django.dispatch import receiver
from django.utils import timezone

from celery import task
from facepy import exceptions

from facebook_auth import forms
from facebook_auth import graph_api
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
        return graph_api.ObservableGraphAPI(self._get_token_object().token)

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
        existing_friends = self.app_friends.all().values_list(
            'user_id', flat=True)
        new_friends = FacebookUser.objects.filter(
            user_id__in=friends_ids).exclude(user_id__in=existing_friends)
        removed_friends = self.app_friends.exclude(user_id__in=friends_ids)
        self.app_friends.add(*new_friends)
        self.app_friends.remove(*removed_friends)


class UserToken(models.Model):
    provider_user_id = models.CharField(max_length=255)
    token = models.TextField(unique=True)
    expiration_date = models.DateTimeField()
    deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User token'
        verbose_name_plural = 'User tokens'


class UserTokenManager(object):
    @staticmethod
    def insert_token(provider_user_id, token, expiration_date):
        provider_user_id = str(provider_user_id)
        defaults = {'provider_user_id': provider_user_id,
                    'expiration_date': expiration_date}
        obj, created = UserToken.objects.get_or_create(
            token=token, defaults=defaults)
        if not created and expiration_date:
            if obj.expiration_date > expiration_date + timedelta(seconds=30):
                extra = {'object_expiration_date': obj.expiration_date,
                         'expiration_date': expiration_date,
                         'token': token}
                logger.warning('Got shorter expiration_date', extra=extra)
            obj.expiration_date = expiration_date
            obj.save()

        if obj.provider_user_id != provider_user_id:
            extra = {'object_provider_user_id': object.provider_user_id,
                     'provider_user_id': provider_user_id,
                     'provider_user_id_type': type(provider_user_id)}
            logger.warning('Got different provider_user_id for token.',
                           extra=extra)

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
    TokenInfo = collections.namedtuple('TokenInfo',
                                       ['user', 'expires', 'token'])

    @staticmethod
    def insert_token(access_token, token_expiration_date, user_id):
        token_manager = UserTokenManager()
        if getattr(settings, 'REQUEST_LONG_LIVED_ACCESS_TOKEN', False):
            insert_extended_token.delay(access_token, user_id)
        token_manager.insert_token(user_id, access_token,
                                   token_expiration_date)

    def discover_fresh_access_token(self, access_token):
        data = self.debug_token(access_token)
        self.insert_token(access_token, data.expires, data.user)

    @staticmethod
    def convert_expiration_seconds_to_date(seconds):
        return timezone.now() + timedelta(seconds=seconds)

    @staticmethod
    def get_long_lived_access_token(access_token):
        graph = graph_api.ObservableGraphAPI()
        args = {
            'client_id': settings.FACEBOOK_APP_ID,
            'client_secret': settings.FACEBOOK_APP_SECRET,
            'grant_type': 'fb_exchange_token',
            'fb_exchange_token': access_token,
        }
        data = graph.get('/oauth/access_token', **args)
        try:
            access_token = urlparse.parse_qs(data)['access_token'][-1]
            expires_in_seconds = int(urlparse.parse_qs(data)['expires'][-1])
        except KeyError:
            logger.warning('Invalid Facebook response.')
            raise FacebookError
        return access_token, expires_in_seconds

    def debug_token(self, token):
        graph = utils.get_application_graph()
        response = graph.get('/debug_token', input_token=token)
        parsed_response = forms.parse_facebook_response(response, token)
        if parsed_response.is_valid:
            data = parsed_response.parsed_data
            self._update_scope(data)
            return self.get_token_info(data)
        else:
            raise ValueError('Invalid Facebook response.',
                             {'errors': parsed_response.errors})

    def _update_scope(self, data):
        if 'scopes' in data:
            (FacebookUser.objects.filter(user_id=data['user_id'])
             .update(scope=','.join(data['scopes'])))

    def get_token_info(self, response_data):
        return self.TokenInfo(token=response_data['token'],
                              user=str(response_data['user_id']),
                              expires=response_data['expires_at'])


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
        access_token, expires_in_seconds = manager.get_long_lived_access_token(
            access_token)
    except (exceptions.FacebookError, FacebookError, HTTPError):
        pass
    else:
        token_expiration_date = manager.convert_expiration_seconds_to_date(
            expires_in_seconds)
        token_manager.insert_token(user_id, access_token,
                                   token_expiration_date)


@receiver(models.signals.post_save, sender=UserToken)
def dispatch_engines_run(sender, instance, created, **kwargs):
    if created:
        debug_all_tokens_for_user.apply_async(args=[instance.provider_user_id],
                                              countdown=45)


@task()
def debug_all_tokens_for_user(user_id):
    manager = FacebookTokenManager()
    token_manager = UserTokenManager()
    user_tokens = UserToken.objects.filter(provider_user_id=user_id,
        deleted=False)
    processed_user_tokens = []
    for token in user_tokens:
        processed_user_tokens.append(token.id)
        try:
            data = manager.debug_token(token.token)
        except ValueError:
            logger.info('Invalid access token')
            token_manager.invalidate_access_token(token.token)
        else:
            token_manager.insert_token(user_id, data.token, data.expires)

    try:
        best_token = token_manager.get_access_token(user_id)
    except UserToken.DoesNotExist:
        pass
    else:
        if best_token.id not in processed_user_tokens:
            logger.info('Retrying debug_all_tokens_for_user.')
            debug_all_tokens_for_user.retry(args=[user_id],
                                            countdown=45)
        else:
            logger.info('Deleting user tokens except best one.')
            tokens_to_delete = sorted(processed_user_tokens)
            tokens_to_delete.remove(best_token.id)
            for token_id in processed_user_tokens:
                UserToken.objects.filter(id=token_id).update(deleted=True)
