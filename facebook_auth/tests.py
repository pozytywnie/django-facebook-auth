from django.test.testcases import TestCase
from ludibrio import Stub
from facepy.exceptions import FacebookError

from backends import _truncate as truncate
from backends import USER_FACTORY, UserFactory

class TruncaterTest(TestCase):
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

class UserFactoryTest(TestCase):
    def test_empty(self):
        profile = {
            'id': '1',
            'first_name': '',
            'last_name': '',
            'email': ''
        }
        USER_FACTORY._product_user('', profile).save()

    def test_no_email(self):
        profile = {
            'id': '1',
            'first_name': '',
            'last_name': '',
        }
        USER_FACTORY._product_user('', profile).save()

    def test_to_long(self):
        profile = {
            'id': '1',
            'first_name': 'a' * 1000,
            'last_name': 'a' * 1000,
            'email': 'a' * 1000
        }
        user = USER_FACTORY._product_user('', profile)
        user.save()

        def get_length(field):
            return user._meta.get_field_by_name(field)[0].max_length

        self.assertEqual(user.first_name, 'a' * get_length('first_name'))
        self.assertEqual(user.last_name, 'a' * get_length('last_name'))
        self.assertEqual(user.email, '')

class UserFactoryOnErrorTest(TestCase):
    def test(self):
        def raise_FB_error(*args, **kwargs):
            raise FacebookError("msg", 1)

        with Stub() as graph_api_class:
            graph_api_class("123").get('me') >> {'id': '123'}
        factory = UserFactory()
        factory.graph_api_class = graph_api_class
        user = factory.get_user("123")
        self.assertEquals(123, user.user_id)

        with Stub() as graph_api_class:
            graph_api_class("123").get >> raise_FB_error
            graph_api_class("123").get >> raise_FB_error
            graph_api_class("123").get('me') >> {'id': '123'}
        factory = UserFactory()
        factory.graph_api_class = graph_api_class
        user = factory.get_user("123")
        self.assertEquals(123, user.user_id)

        with Stub() as graph_api_class:
            graph_api_class("123").get >> raise_FB_error
            graph_api_class("123").get >> raise_FB_error
            graph_api_class("123").get >> raise_FB_error
            graph_api_class("123").get('me') >> {'id': '123'}
        factory = UserFactory()
        factory.graph_api_class = graph_api_class
        self.assertRaises(FacebookError, lambda: factory.get_user("123"))
