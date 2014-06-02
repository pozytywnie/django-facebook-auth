try:
    from unittest import mock
    MOCK_CLASS_NAME = 'unittest.mock.Mock'
except ImportError:
    import mock
    MOCK_CLASS_NAME = 'mock.Mock'

import datetime

from django import test

from facepy.exceptions import FacebookError

from facebook_auth.backends import _truncate as truncate
from facebook_auth.backends import UserFactory
from facebook_auth import graph_api


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
