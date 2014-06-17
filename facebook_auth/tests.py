try:
    from unittest import mock
    MOCK_CLASS_NAME = 'unittest.mock.Mock'
except ImportError:
    import mock
    MOCK_CLASS_NAME = 'mock.Mock'

import datetime

from django import test

from facepy.exceptions import FacebookError
import pytz

from facebook_auth.backends import _truncate as truncate
from facebook_auth.backends import UserFactory
from facebook_auth import forms
from facebook_auth import graph_api
from facebook_auth import models


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
    def test_empty(self):
        profile = {
            'id': '1',
            'first_name': '',
            'last_name': '',
            'email': ''
        }
        UserFactory()._product_user('', profile).save()

    def test_no_email(self):
        profile = {
            'id': '1',
            'first_name': '',
            'last_name': '',
        }
        UserFactory()._product_user('', profile).save()

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
            return user._meta.get_field_by_name(field)[0].max_length

        self.assertEqual(user.first_name, 'a' * get_length('first_name'))
        self.assertEqual(user.last_name, 'a' * get_length('last_name'))
        self.assertEqual(user.email, '')


class UserFactoryOnErrorTest(test.TestCase):
    def test(self):
        factory = UserFactory()
        factory.graph_api_class = mock.Mock()
        factory.graph_api_class.return_value.get.return_value = {'id': '123'}
        user = factory.get_user("123")
        self.assertEqual(123, user.user_id)

        factory = UserFactory()
        factory.graph_api_class = mock.Mock()
        factory.graph_api_class.return_value.get.side_effect = [
            FacebookError("msg", 1),
            FacebookError("msg", 1),
            {'id': '123'}]

        user = factory.get_user("123")
        self.assertEqual(123, user.user_id)

        factory = UserFactory()
        factory.graph_api_class = mock.Mock()
        factory.graph_api_class.return_value.get.side_effect = [
            FacebookError("msg", 1),
            FacebookError("msg", 1),
            FacebookError("msg", 1),
            {'id': '123'}]
        self.assertEqual(None, factory.get_user("123"))


@mock.patch('django.utils.timezone.now')
@mock.patch('facepy.GraphAPI._query')
@mock.patch('facebook_auth.graph_api.GRAPH_OBSERVER_CLASSES')
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
    def test_simple_insert(self):
        manager = models.UserTokenManager
        manager.insert_token('123', 'abc123',
                             datetime.datetime(1989, 2, 25, tzinfo=pytz.utc))
        token = manager.get_access_token('123')
        self.assertEqual('abc123', token.token)

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

    def test_invalidating_token(self):
        manager = models.UserTokenManager
        manager.insert_token('123', 'abc123',
                             datetime.datetime(1989, 2, 25, tzinfo=pytz.utc))
        manager.invalidate_access_token('abc123')
        self.assertRaises(models.UserToken.DoesNotExist,
                          manager.get_access_token, '123')


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
        manager.debug_token.side_effect = ValueError
        token_manager = models.UserTokenManager()
        token_manager.insert_token('123', 'token1212', "2014-02-02")
        models.debug_all_tokens_for_user('123')
        self.assertRaises(models.UserToken.DoesNotExist,
                          token_manager.get_access_token, '123')
