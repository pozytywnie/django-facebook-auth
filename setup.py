#!/usr/bin/env python
from distutils.core import setup

def read(name):
    from os import path
    return open(path.join(path.dirname(__file__), name)).read()

setup(
    name='django-facebook-auth',
    version='2.5',
    description="Authorisation app for Facebook API.",
    long_description=read("README.rst"),
    maintainer="Tomasz Wysocki",
    maintainer_email="tomasz@wysocki.info",

    install_requires=(
        'django',
        'facepy',
        'simplejson',
    ),

    packages=[
        'facebook_auth',
        'facebook_auth.migrations',
    ],
)

