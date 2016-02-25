from . import graph_api


def get_graph(*args, **kwargs):
    return graph_api.ObservableGraphAPI(*args, **kwargs)
