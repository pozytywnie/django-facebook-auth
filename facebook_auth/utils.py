from django.conf import settings
import facepy

from facebook_auth import graph_api

GRAPH_MAX_TRIES = 3


def get_from_graph_api(graphAPI, query):
    for i in range(GRAPH_MAX_TRIES):
        try:
            return graphAPI.get(query)
        except facepy.FacepyError as e:
            if i == GRAPH_MAX_TRIES - 1 or getattr(e, 'code', None) != 1:
                raise


def get_application_graph():
    token = facepy.utils.get_application_access_token(
            settings.FACEBOOK_APP_ID, settings.FACEBOOK_APP_SECRET,
            api_version='2.1')
    return graph_api.get_graph(token)
