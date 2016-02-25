import logging

from facepy import exceptions

from . import graph_api

try:
    import urllib.parse as urlparse
except ImportError:
    import urlparse

logger = logging.getLogger(__name__)


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
        access_token = urlparse.parse_qs(data)['access_token'][-1]
        expires_in_seconds = int(urlparse.parse_qs(data)['expires'][-1])
    except KeyError:
        logger.warning('Invalid Facebook response.')
        raise FacebookError
    return access_token, expires_in_seconds


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
        return _extract_access_token(data)
    except TokenParsingError as e:
        args['client_secret'] = '*******%s' % args['client_secret'][-4:]
        logger.error(e, extra={'facebook_response': data,
                               'sent_args': args})
        raise


def _extract_access_token(data):
    if isinstance(data, dict):
        try:
            return data['access_token']
        except KeyError as e:
            raise TokenParsingError(e)
    else:
        try:
            return urlparse.parse_qs(data)['access_token'][-1]
        except KeyError as e:
            raise TokenParsingError(e)


class FacebookError(Exception):
    pass


class TokenParsingError(Exception):
    pass
