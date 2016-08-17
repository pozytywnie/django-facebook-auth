try:
    from unittest import mock
    from urllib import parse
    MOCK_CLASS_NAME = 'unittest.mock.Mock'
except ImportError:
    import mock
    import urlparse as parse
    MOCK_CLASS_NAME = 'mock.Mock'

import collections
import datetime

from django.core.cache import cache
from django import test

from facepy.exceptions import FacebookError
import pytz

from facebook_auth.backends import _truncate as truncate
from facebook_auth.backends import UserFactory
from facebook_auth import forms
from facebook_auth.facepy_wrapper import utils as wrapper_utils
from facebook_auth.facepy_wrapper import graph_api
from facebook_auth import models
from facebook_auth import utils
from facebook_auth import views


class TruncaterTest(test.SimpleTestCase):
    def test_empty(self):
        self.assertEqual('', truncate('', 30))

    def test_no_cutting(self):
        word = 'abcde'
        self.assertEqual(word, truncate(word, 10))
        self.assertEqual(word, truncate(word, 6))
        self.assertEqual(word, truncate(word, 5))

    def test_cutting(self):
        word = 'abcde'
        self.assertEqual(word[:4], truncate(word, 4))
        self.assertEqual(word[:3], truncate(word, 3))
        self.assertEqual('', truncate(word, 0))

    def test_to_zero_cut(self):
        word = 'abcde'
        self.assertEqual(word, truncate(word, 10, to_zero=True))
        self.assertEqual(word, truncate(word, 6, to_zero=True))
        self.assertEqual(word, truncate(word, 5, to_zero=True))
        self.assertEqual('', truncate(word, 4, to_zero=True))
        self.assertEqual('', truncate(word, 3, to_zero=True))
        self.assertEqual('', truncate(word, 0, to_zero=True))


class UserFactoryTest(test.TestCase):
    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_empty(self):
        profile = {
            'id': '1',
            'first_name': '',
            'last_name': '',
            'email': ''
        }
        UserFactory()._product_user('', profile).save()

    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_no_email(self):
        profile = {
            'id': '1',
            'first_name': '',
            'last_name': '',
        }
        UserFactory()._product_user('', profile).save()

    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_to_long(self):
        profile = {
            'id': '1',
            'first_name': 'a' * 1000,
            'last_name': 'a' * 1000,
            'email': 'a' * 1000
        }
        user = UserFactory()._product_user('', profile)
        user.save()

        def get_length(field):
            return user._meta.get_field(field).max_length

        self.assertEqual(user.first_name, 'a' * get_length('first_name'))
        self.assertEqual(user.last_name, 'a' * get_length('last_name'))
        self.assertEqual(user.email, '')


@mock.patch('facebook_auth.utils.get_graph')
class UserFactoryOnErrorTest(test.TestCase):
    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_success(self, get_graph):
        factory = UserFactory()
        get_graph.return_value.get.return_value = {'id': '123'}
        user = factory.get_user("123")
        self.assertEqual(123, user.user_id)

    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_success_in_retry(self, get_graph):
        factory = UserFactory()
        get_graph.return_value.get.side_effect = [
            FacebookError("msg", 1),
            FacebookError("msg", 1),
            {'id': '123'}]

        user = factory.get_user("123")
        self.assertEqual(123, user.user_id)

    def test_failure(self, get_graph):
        factory = UserFactory()
        get_graph.return_value.get.side_effect = [
            FacebookError("msg", 1),
            FacebookError("msg", 1),
            FacebookError("msg", 1),
            {'id': '123'}]
        with self.assertRaises(FacebookError):
            factory.get_user("123")


@mock.patch('django.utils.timezone.now')
@mock.patch('facepy.GraphAPI._query')
@mock.patch('facebook_auth.facepy_wrapper.graph_api.GRAPH_OBSERVER_CLASSES')
class ObservableGraphApiTest(test.SimpleTestCase):
    def test_query_failure(self, observers, query, now):
        now.side_effect = [
            datetime.datetime(year=1, month=1, day=1, minute=1),
            datetime.datetime(year=1, month=1, day=1, minute=2),
        ]
        query.side_effect = FacebookError("msg", 1)
        observer_cls = mock.Mock()
        observers.__iter__.return_value = [observer_cls]
        with self.assertRaises(FacebookError):
            graph_api.ObservableGraphAPI().get('me')
        observer_cls.return_value.handle_facebook_communication.assert_called_once_with()
        observer_cls.assert_called_once_with(None, None, query.side_effect,
                                             datetime.timedelta(minutes=1))

    def test_query_success_string(self, observers, query, now):
        now.side_effect = [
            datetime.datetime(year=1, month=1, day=1, minute=1),
            datetime.datetime(year=1, month=1, day=1, minute=2),
        ]
        query.return_value = 'some string response'
        observer_cls = mock.Mock()
        observers.__iter__.return_value = [observer_cls]
        graph_api.ObservableGraphAPI().get('me')
        observer_cls.return_value.handle_facebook_communication.assert_called_once_with()
        observer_cls.assert_called_once_with(None, None, None,
                                             datetime.timedelta(minutes=1))


class GraphObserversTest(test.SimpleTestCase):
    def test_getting_observer_classes(self):
        classes = graph_api.get_graph_observer_classes([MOCK_CLASS_NAME])
        self.assertEqual([mock.Mock], list(classes))

    def test_iterating_observer_classes_twice(self):
        classes = graph_api.get_graph_observer_classes([MOCK_CLASS_NAME])
        list(classes)
        self.assertEqual([mock.Mock], list(classes))


class UserTokenManagerTest(test.TestCase):
    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_simple_insert(self):
        manager = models.UserTokenManager
        manager.insert_token('123', 'abc123',
                             datetime.datetime(1989, 2, 25, tzinfo=pytz.utc))
        token = manager.get_access_token('123')
        self.assertEqual('abc123', token.token)

    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_multiple_inserts(self):
        manager = models.UserTokenManager
        manager.insert_token('123', 'abc123',
                             datetime.datetime(1989, 2, 25, tzinfo=pytz.utc))
        manager.insert_token('456', 'abc456',
                             datetime.datetime(1989, 2, 25, tzinfo=pytz.utc))
        token = manager.get_access_token('123')
        self.assertEqual('abc123', token.token)

        token2 = manager.get_access_token('456')
        self.assertEqual('abc456', token2.token)

    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_invalidating_token(self):
        manager = models.UserTokenManager
        manager.insert_token('123', 'abc123',
                             datetime.datetime(1989, 2, 25, tzinfo=pytz.utc))
        manager.invalidate_access_token('abc123')
        self.assertRaises(models.UserToken.DoesNotExist,
                          manager.get_access_token, '123')

    @mock.patch('django.utils.timezone.now',
                return_value=datetime.datetime(1989, 1, 1, tzinfo=pytz.utc))
    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_getting_wildcarded_token_first(self, _):
        models.UserToken.objects.create(
            provider_user_id='555',
            token='WildcardedToken',
            expiration_date=None,
        )
        models.UserToken.objects.create(
            provider_user_id='555',
            token='ImCrap',
            expiration_date=datetime.datetime(4444, 1, 1, tzinfo=pytz.utc),
        )
        models.UserToken.objects.create(
            provider_user_id='555',
            token='ImCrapToo',
            expiration_date=datetime.datetime(1989, 1, 1, tzinfo=pytz.utc),
        )
        models.UserToken.objects.create(
            provider_user_id='555',
            token='ImCrapThree',
            expiration_date=datetime.datetime(4444, 1, 1, tzinfo=pytz.utc),
        )
        manager = models.UserTokenManager
        token = manager.get_access_token('555')
        self.assertEqual('WildcardedToken', token.token)

    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_getting_latest_token_on_no_wildcarded(self):
        models.UserToken.objects.create(
            provider_user_id='555',
            token='ImCrapSorry',
            expiration_date=datetime.datetime(1989, 1, 1, tzinfo=pytz.utc),
        )
        models.UserToken.objects.create(
            provider_user_id='555',
            token='lastExpiring',
            expiration_date=datetime.datetime(4444, 1, 1, tzinfo=pytz.utc),
        )
        models.UserToken.objects.create(
            provider_user_id='555',
            token='ImCrapDontLaughAtMe',
            expiration_date=datetime.datetime(2000, 1, 1, tzinfo=pytz.utc),
        )
        manager = models.UserTokenManager
        token = manager.get_access_token('555')
        self.assertEqual('lastExpiring', token.token)

    @mock.patch('django.utils.timezone.now')
    @mock.patch('facebook_auth.models.FacebookTokenManager.debug_all_user_tokens', mock.Mock())
    def test_getting_latest_token_on_expired_wildcarded(self, now):
        now.return_value = datetime.datetime(1989, 1, 1, tzinfo=pytz.utc)
        models.UserToken.objects.create(
            provider_user_id='555',
            token='WithExpirationDate',
            expiration_date=datetime.datetime(4444, 1, 1, tzinfo=pytz.utc),
        )
        now.return_value = datetime.datetime(1, 1, 1, tzinfo=pytz.utc)
        models.UserToken.objects.create(
            provider_user_id='555',
            token='ExpiredJesusToken',
            expiration_date=None,
        )
        now.return_value = datetime.datetime(1989, 1, 1, tzinfo=pytz.utc)
        manager = models.UserTokenManager
        token = manager.get_access_token('555')
        self.assertEqual('WithExpirationDate', token.token)

    def test_getting_raising_error_on_no_token(self):
        manager = models.UserTokenManager
        self.assertRaises(models.UserToken.DoesNotExist,
                          manager.get_access_token, '555')


class TestParseFacebookResponse(test.SimpleTestCase):
    def test_without_data(self):
        response = forms.parse_facebook_response({}, '123')
        self.assertEqual(response.is_valid, False)

    def test_with_empty_data(self):
        response = forms.parse_facebook_response({'data': {}}, '123')
        self.assertEqual(response.is_valid, False)

    def test_if_original_dict_is_not_modified(self):
        data = {}
        input_json = {'data': data}
        forms.parse_facebook_response(input_json, '123')
        self.assertEqual({}, data)
        self.assertEqual({'data': {}}, input_json)

    def test_is_valid_as_string(self):
        data = {
            'expires_at': 12341234,
            'is_valid': 'foo',
            'scopes[]': 'foo,bar',
            'user_id': '123',
        }
        response = forms.parse_facebook_response({'data': data}, '123')
        self.assertEqual(response.is_valid, True)

    def test_valid_response(self):
        data = {
            'expires_at': 12341234,
            'is_valid': True,
            'scopes[]': 'foo,bar',
            'user_id': '123',
        }
        response = forms.parse_facebook_response({'data': data}, '123')
        self.assertEqual(response.is_valid, True)

    def test_valid_real_data(self):
        data = {
            "expires_at": 1403429380,
            "scopes": [
              "public_profile",
              "basic_info",
              "publish_checkins",
              "status_update",
              "photo_upload",
              "video_upload",
              "email",
              "create_note",
              "share_item",
              "publish_stream",
              "publish_actions",
              "user_friends"
            ],
            "app_id": 423260947733647,
            "application": "'Social WiFi'",
            "issued_at": 1398245380,
            "is_valid": True,
            "user_id": 1000066666,
        }
        response = forms.parse_facebook_response({'data': data}, '123')
        self.assertEqual(response.is_valid, True)

    def test_test_strange_types(self):
        data = {
            'expires_at': {},
            'is_valid': [],
            'scopes[]': {},
            'user_id': 1.1,
        }
        response = forms.parse_facebook_response({'data': data}, '123')
        self.assertEqual(response.is_valid, False)

    def test_data_as_list(self):
        response = forms.parse_facebook_response({'data': []}, '123')
        self.assertEqual(response.is_valid, False)

    def test_data_as_int(self):
        response = forms.parse_facebook_response({'data': []}, '123')
        self.assertEqual(response.is_valid, False)

    def test_bool_response(self):
        response = forms.parse_facebook_response(False, '123')
        self.assertEqual(response.is_valid, False)


class TestDebugAllTokensForUser(test.TestCase):
    def tearDown(self):
        cache.clear()

    @mock.patch.object(models, 'FacebookTokenManager')
    def test_positive_scenario(self, FacebookTokenManager):
        manager = FacebookTokenManager.return_value
        parsed_data = manager.debug_token.return_value
        parsed_data.token = 'token1212'
        parsed_data.expires = datetime.datetime(2014, 2, 2, tzinfo=pytz.utc)
        token_manager = models.UserTokenManager()
        token_manager.insert_token('123', 'token1212', "2014-02-02")
        models.debug_all_tokens_for_user('123')
        token = token_manager.get_access_token('123')
        self.assertFalse(token.deleted)

    @mock.patch.object(models, 'FacebookTokenManager')
    def test_negative_scenario(self, FacebookTokenManager):
        manager = FacebookTokenManager.return_value
        manager.debug_token.side_effect = models.TokenDebugException
        token_manager = models.UserTokenManager()
        token_manager.insert_token('123', 'token1212', "2014-02-02")
        models.debug_all_tokens_for_user('123')
        self.assertRaises(models.UserToken.DoesNotExist,
                          token_manager.get_access_token, '123')

    @mock.patch('facebook_auth.models.debug_all_tokens_for_user')
    def test_caching_for_single_user(self, debug_all_tokens_for_user):
        models.FacebookTokenManager.debug_all_user_tokens(1)
        models.FacebookTokenManager.debug_all_user_tokens(1)
        self.assertEqual([
            mock.call.apply_async(args=[1], countdown=45),
        ], debug_all_tokens_for_user.mock_calls)

    @mock.patch('facebook_auth.models.debug_all_tokens_for_user')
    def test_caching_for_two_users(self, debug_all_tokens_for_user):
        models.FacebookTokenManager.debug_all_user_tokens(1)
        models.FacebookTokenManager.debug_all_user_tokens(2)
        self.assertEqual([
            mock.call.apply_async(args=[1], countdown=45),
            mock.call.apply_async(args=[2], countdown=45),
        ], debug_all_tokens_for_user.mock_calls)


class TestNextUrl(test.TestCase):
    def test_invalid_next(self):
        with self.assertRaises(utils.InvalidNextUrl):
            utils.Next().decode('1:2:3')

    def test_invalid_next_format(self):
        with self.assertRaises(utils.InvalidNextUrl):
            utils.Next().decode('this is not valid signature')

    def test_empty_next(self):
        with self.assertRaises(utils.InvalidNextUrl):
            utils.Next().decode('')

    def test_if_encoding_is_dictionary_order_independent(self):
        ordered = collections.OrderedDict([('A', 'a'), ('B', 'b')])
        reverse_ordered = collections.OrderedDict([('B', 'b'), ('A', 'a')])
        self.assertEqual(utils.Next().encode(ordered),
                         utils.Next().encode(reverse_ordered))

    @mock.patch('django.core.signing.time.time')
    def test_if_encoding_does_not_vary_in_time(self, time):
        data = {'a': 3}
        time.return_value = 16
        old = utils.Next().encode(data)
        time.return_value = 42
        new = utils.Next().encode(data)
        self.assertEqual(old, new)


class HandlerAcceptanceTest(test.TestCase):
    @mock.patch('facebook_auth.views.authenticate')
    def test_valid_next(self, authenticate):
        authenticate.return_value = None
        encoded_next = utils.Next().encode({
            'next': 'http://next.example.com',
            'close': 'http://close.example.com'})
        next_value = parse.parse_qs(encoded_next)['next'][0]
        request = mock.Mock(GET={'next': next_value, 'code': 'code'},
                            method='GET')
        with self.settings(FACEBOOK_CANVAS_URL='http://example.com'):
            response = views.handler(request)
        self.assertEqual(302, response.status_code)
        self.assertEqual('http://next.example.com', response['Location'])

    def test_invalid_next(self):
        request = mock.Mock(GET={'next': 'a:b:c', 'code': 'code'},
                            method='GET')
        response = views.handler(request)
        self.assertEqual(400, response.status_code)

    def test_without_next(self):
        request = mock.Mock(GET={'code': 'code'}, method='GET')
        response = views.handler(request)
        self.assertEqual(400, response.status_code)


class FacebookBackendTest(test.TestCase):
    def test_extract_access_token_pre2_3(self):
        access_token = wrapper_utils._parse_access_token_response('access_token=token&expires=5121505')
        self.assertEqual('token', access_token.access_token)
        self.assertEqual(5121505, access_token.expires_in_seconds)

    def test_extract_access_token_post2_3(self):
        access_token = wrapper_utils._parse_access_token_response({
            'access_token': 'token',
            'expires_in': 5121505,
            'token_type': 'bearer'
        })
        self.assertEqual('token', access_token.access_token)
        self.assertEqual(5121505, access_token.expires_in_seconds)
