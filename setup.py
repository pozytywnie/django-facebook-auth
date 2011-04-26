#!/usr/bin/env python
from distutils.core import setup

setup(
    name='django-facebook-auth',
    version='0.1.2',
    description="Authorisation app for Facebook API.",
    maintainer="Tomasz Wysocki",
    maintainer_email="tomasz@wysocki.info",

    install_requires=(
        'django',
        'django-package-installer',
        'facebook-python-sdk',
        'simplejson',
    ),

    packages=[
        'facebook_auth',
    ],
)

