#!/usr/bin/env python
from setuptools import setup


def read(name):
    from os import path
    return open(path.join(path.dirname(__file__), name)).read()

setup(
    name='django-facebook-auth',
    version='3.9.0',
    description="Authorisation app for Facebook API.",
    long_description=read("README.rst"),
    url="https://github.com/pozytywnie/django-facebook-auth",
    maintainer="Tomasz Wysocki",
    maintainer_email="tomasz@wysocki.info",

    install_requires=(
        'celery',
        'Django',
        'facepy>=1.0.6',
        'cached_property',
    ),

    packages=[
        'facebook_auth',
        'facebook_auth.migrations',
        'facebook_auth.management',
        'facebook_auth.management.commands',
        'facebook_auth.south_migrations',
        'facebook_auth.facepy_wrapper',
    ],
)
