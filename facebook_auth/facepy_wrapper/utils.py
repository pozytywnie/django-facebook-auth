import collections
import logging

from facepy import exceptions

from . import graph_api

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

logger = logging.getLogger(__name__)

AccessTokenResponse = collections.namedtuple('AccessTokenResponse', ['access_token', 'expires_in_seconds'])


def get_graph(*args, **kwargs):
    return graph_api.ObservableGraphAPI(*args, **kwargs)


def get_long_lived_access_token(access_token, client_id, client_secret):
    graph = get_graph()
    args = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'fb_exchange_token',
        'fb_exchange_token': access_token,
    }
    data = graph.get('/oauth/access_token', **args)
    try:
        return _parse_access_token_response(data)
    except TokenParsingError:
        logger.warning('Invalid Facebook response.')
        raise


def get_access_token(client_id, client_secret, code=None, redirect_uri=None, timeout=None):
    graph = get_graph(timeout=timeout)
    args = {
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
        'code': code
    }
    try:
        data = graph.get('/oauth/access_token', **args)
    except exceptions.FacepyError:
        logger.warning("Facebook login connection error")
        raise
    try:
        return _parse_access_token_response(data).access_token
    except TokenParsingError as e:
        args['client_secret'] = '*******%s' % args['client_secret'][-4:]
        logger.error(e, extra={'facebook_response': data,
                               'sent_args': args})
        raise


def _parse_access_token_response(data):
    if isinstance(data, dict):
        try:
            access_token = data['access_token']
            expires_in_seconds = int(data['expires_in'])
        except KeyError as e:
            raise TokenParsingError(e)
    else:
        parsed_qs_data = urlparse.parse_qs(data)
        try:
            access_token = parsed_qs_data['access_token'][-1]
            expires_in_seconds = int(parsed_qs_data['expires'][-1])
        except KeyError as e:
            raise TokenParsingError(e)
    return AccessTokenResponse(access_token=access_token, expires_in_seconds=expires_in_seconds)


class FacebookError(Exception):
    pass


class TokenParsingError(Exception):
    pass
