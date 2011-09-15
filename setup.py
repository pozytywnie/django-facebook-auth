#!/usr/bin/env python
from distutils.core import setup

setup(
    name='django-facebook-auth',
    version='0.1.3.1',
    description="Authorisation app for Facebook API.",
    maintainer="Tomasz Wysocki",
    maintainer_email="tomasz@wysocki.info",

    install_requires=(
        'django',
        'django-package-installer',
        'facebook-python-sdk',
        'simplejson',
        'south',
    ),

    packages=[
        'facebook_auth',
        'facebook_auth.migrations',
    ],
)

