#!/usr/bin/env python
from distutils.core import setup

def read(name):
    return open(path.join(path.dirname(__file__), name)).read()

setup(
    name='django-facebook-auth',
    version='1.1.0',
    description="Authorisation app for Facebook API.",
    long_description=read("README.rst"),
    maintainer="Tomasz Wysocki",
    maintainer_email="tomasz@wysocki.info",

    install_requires=(
        'django',
        'facebook-python-sdk',
        'simplejson',
        'south',
    ),

    packages=[
        'facebook_auth',
        'facebook_auth.migrations',
    ],
)

