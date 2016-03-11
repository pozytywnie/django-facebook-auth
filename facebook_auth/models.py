import collections
import json
import logging
from datetime import timedelta
from cached_property import cached_property

try:
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import HTTPError


from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import models as auth_models
from django.db import models
from django.dispatch import receiver
from django.utils import timezone

from celery import task
from facepy import exceptions

from facebook_auth import forms
from facebook_auth import utils
from facebook_auth.facepy_wrapper.utils import TokenParsingError

logger = logging.getLogger(__name__)


class FacebookUser(auth_models.User):
    user_id = models.BigIntegerField(unique=True)
    app_friends = models.ManyToManyField('self')
    scope = models.CharField(max_length=512, blank=True, default='')

    @property
    def access_token(self):
        try:
            return self._token_object.token
        except UserToken.DoesNotExist:
            return None

    @property
    def access_token_expiration_date(self):
        return self._token_object.expiration_date

    @property
    def graph(self):
        return utils.get_graph(self._token_object.token)

    @cached_property
    def _token_object(self):
        return UserTokenManager.get_access_token(self.user_id)

    @property
    def js_session(self):
        return json.dumps({
            'access_token': self.access_token,
            'uid': self.user_id,
        })

    @property
    def friends(self):
        response = utils.get_from_graph_api(self.graph, "me/friends")
        if 'data' in response:
            return response['data']
        else:
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
    granted_at = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateTimeField(null=True, blank=True, default=None)
    deleted = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'User token'
        verbose_name_plural = 'User tokens'


class TokenDebugException(Exception):
    pass


class UserTokenManager(object):
    @staticmethod
    def insert_token(provider_user_id, token, expiration_date=None):
        provider_user_id = str(provider_user_id)
        defaults = {'provider_user_id': provider_user_id,
                    'expiration_date': expiration_date}
        obj, created = UserToken.objects.get_or_create(
            token=token, defaults=defaults)
        if not created:
            obj.expiration_date = expiration_date
            obj.save()

        if obj.provider_user_id != provider_user_id:
            extra = {'object_provider_user_id': obj.provider_user_id,
                     'provider_user_id': provider_user_id,
                     'provider_user_id_type': type(provider_user_id)}
            logger.warning('Got different provider_user_id for token.',
                           extra=extra)

    @staticmethod
    def get_access_token(provider_user_id):
        eldest_wildcarded = timezone.now() - timezone.timedelta(seconds=30)
        related_tokens = UserToken.objects.filter(
            provider_user_id=provider_user_id, deleted=False)
        try:
            return (related_tokens
                    .filter(expiration_date__isnull=True,
                            granted_at__gte=eldest_wildcarded)
                    .latest('granted_at'))
        except UserToken.DoesNotExist:
            return (related_tokens
                    .exclude(expiration_date__isnull=True)
                    .latest('expiration_date'))

    @staticmethod
    def invalidate_access_token(token):
        UserToken.objects.filter(token=token).update(deleted=True)


class FacebookTokenManager(object):
    DEBUG_ALL_USER_TOKENS_PERIOD = getattr(settings, 'FACEBOOK_AUTH_DEBUG_ALL_USER_TOKENS_PERIOD', timedelta(minutes=5))
    TokenInfo = collections.namedtuple('TokenInfo',
                                       ['user', 'expires', 'token'])

    @staticmethod
    def insert_token(access_token, user_id, token_expiration_date=None):
        token_manager = UserTokenManager()
        if getattr(settings, 'REQUEST_LONG_LIVED_ACCESS_TOKEN', False):
            insert_extended_token.delay(access_token, user_id)
        token_manager.insert_token(user_id, access_token,
                                   token_expiration_date)

    def discover_fresh_access_token(self, access_token):
        data = self.debug_token(access_token)
        self.insert_token(access_token, data.user, data.expires)

    @staticmethod
    def convert_expiration_seconds_to_date(seconds):
        return timezone.now() + timedelta(seconds=seconds)

    @staticmethod
    def get_long_lived_access_token(access_token):
        return utils.get_long_lived_access_token(access_token)

    def debug_token(self, token):
        graph = utils.get_application_graph()
        response = graph.get('/debug_token', input_token=token)
        parsed_response = forms.parse_facebook_response(response, token)
        if parsed_response.is_valid:
            data = parsed_response.parsed_data
            self._update_scope(data)
            return self.get_token_info(data)
        else:
            raise TokenDebugException('Invalid Facebook response.',
                                      {'errors': parsed_response.errors})

    def _update_scope(self, data):
        if 'scopes' in data:
            (FacebookUser.objects.filter(user_id=data['user_id'])
             .update(scope=','.join(data['scopes'])))

    def get_token_info(self, response_data):
        return self.TokenInfo(token=response_data['token'],
                              user=str(response_data['user_id']),
                              expires=response_data['expires_at'])

    @classmethod
    def debug_all_user_tokens(cls, user_id):
        key = 'facebook_auth_debug_all_user_tokens-{}'.format(user_id)
        if cache.get(key) is None:
            cache.set(key, 1, cls.DEBUG_ALL_USER_TOKENS_PERIOD.total_seconds())
            try:
                debug_all_tokens_for_user.apply_async(
                    args=[user_id], countdown=45)
            except OSError:
                logger.error("Couldn't run debug_all_tokens_for_user due to celery"
                             " connection error.")


@task()
def validate_token(access_token):
    manager = FacebookTokenManager()
    try:
        manager.debug_token(access_token)
    except TokenDebugException:
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
    except (exceptions.FacebookError, TokenParsingError, HTTPError):
        pass
    else:
        token_expiration_date = manager.convert_expiration_seconds_to_date(
            expires_in_seconds)
        token_manager.insert_token(user_id, access_token,
                                   token_expiration_date)


@receiver(models.signals.post_save, sender=UserToken)
def dispatch_engines_run(sender, instance, created, **kwargs):
    if created:
        FacebookTokenManager.debug_all_user_tokens(instance.provider_user_id)


@task()
def debug_all_tokens_for_user(user_id):
    manager = FacebookTokenManager()
    token_manager = UserTokenManager()
    user_tokens = list(
        UserToken.objects
        .filter(provider_user_id=user_id, deleted=False)
        .values_list('token', flat=True)
    )
    for token in user_tokens:
        try:
            data = manager.debug_token(token)
        except TokenDebugException:
            logger.info('Invalid access token')
            token_manager.invalidate_access_token(token)
        else:
            token_manager.insert_token(user_id, data.token, data.expires)
    try:
        best_token = token_manager.get_access_token(user_id)
    except UserToken.DoesNotExist:
        logger.info("Best token was deleted by other process.")
    else:
        if best_token.token not in user_tokens:
            logger.info(
                'New best token has arrived.'
                'Retrying debug_all_tokens_for_user.'
            )
            debug_all_tokens_for_user.retry(args=[user_id],
                                            countdown=45)
        else:
            logger.info('Deleting user tokens except best one.')
            tokens_to_delete = sorted(user_tokens)
            tokens_to_delete.remove(best_token.token)
            for token in tokens_to_delete:
                token_manager.invalidate_access_token(token)
