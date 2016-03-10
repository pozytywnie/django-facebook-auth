import logging
from datetime import datetime

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

from django.conf import settings
from django.utils import timezone

from facepy import exceptions

from facebook_auth import models
from facebook_auth import utils
from facebook_auth.facepy_wrapper.utils import TokenParsingError

logger = logging.getLogger(__name__)


def _truncate(word, length, to_zero=False):
    if to_zero and len(word) > length:
        return word[0:0] # preserve type
    else:
        return word[:length]


class UserFactory(object):
    user_facebook_fields = ['first_name', 'last_name', 'email', 'name']

    fallback_expiration_date = datetime(1990, 10, 10, 0, 0, 1).replace(
        tzinfo=timezone.utc)

    def __create_username(self, profile):
            return profile['id']  # TODO better username

    def _product_user(self, access_token, profile):
        user_id = int(profile['id'])
        username = self.__create_username(profile)
        user, created = models.FacebookUser.objects.get_or_create(
            user_id=user_id, defaults={'username': username})

        if user.username != username:
            logger.warning('FacebookUser username mismatch', extra={
                'old_username': user.username,
                'new_username': username,
                'user_django_id': user.id,
                'user_facebook_id': user_id,
                'user_email': user.email
            })
        if created:
            user.set_unusable_password()

        def copy_field(field, to_zero=False):
            if field in profile:
                length = user._meta.get_field(field).max_length
                setattr(user, field, _truncate(profile[field], length,
                        to_zero=to_zero))

        copy_field('email', True)
        copy_field('first_name')
        copy_field('last_name')
        if access_token is not None:
            models.FacebookTokenManager().insert_token(
                access_token, str(user.user_id))
        user.save()
        self.create_profile_object(profile, user)
        return user

    def get_user(self, access_token):
        fields = ','.join(self.user_facebook_fields)
        profile = utils.get_from_graph_api(
            utils.get_graph(access_token),
            'me?fields=%s' % fields)
        return self._product_user(access_token, profile)

    def _get_fallback_expiration_date(self):
        logger.warning('Deprecated fallback expiration_date used.')
        return self.fallback_expiration_date

    def get_user_by_id(self, uid):
        api = utils.get_application_graph(
            version=settings.FACEBOOK_API_VERSION
        )
        profile = utils.get_from_graph_api(api, uid)
        return self._product_user(None, profile)

    def create_profile_object(self, profile, user):
        if 'facebook_profile' in settings.INSTALLED_APPS:
            from facebook_profile import models as profile_models
            from facebook_profile import parser as profile_parser
            parser = profile_parser.FacebookDataParser(profile, True, True)
            try:
                data = parser.run()
                profile = (profile_models.FacebookUserProfile
                           .objects.create_or_update(data))
                profile.user = user
                profile.save()
            except profile_parser.FacebookDataParserCriticalError:
                pass


USER_FACTORY = UserFactory()


class FacebookBackend(object):
    def authenticate(self, code=None, redirect_uri=None):
        try:
            access_token = utils.get_access_token(code=code, redirect_uri=redirect_uri)
        except exceptions.FacebookError as e:
            message = "Facebook login failed %s" % e.message
            code_used_message = 'This authorization code has been used.'
            if e.code == 100 and e.message == code_used_message:
                logger.info(message)
                return None
            else:
                logger.warning(message)
                raise
        except TokenParsingError:
            return None
        else:
            user = USER_FACTORY.get_user(access_token)
            return user

    @staticmethod
    def _timestamp_to_datetime(timestamp):
        naive = datetime.fromtimestamp(int(timestamp))
        return naive.replace(tzinfo=timezone.utc)

    def get_user(self, user_id):
        try:
            return models.FacebookUser.objects.get(pk=user_id)
        except models.FacebookUser.DoesNotExist: #@UndefinedVariable
            return None


class FacebookJavascriptBackend(FacebookBackend):
    def authenticate(self, access_token):
        return USER_FACTORY.get_user(access_token)
