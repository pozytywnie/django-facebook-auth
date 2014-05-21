django-facebook-auth
========================

.. image:: https://travis-ci.org/pozytywnie/django-facebook-auth.svg
   :target: https://travis-ci.org/pozytywnie/django-facebook-auth

Installation
------------

Package
_______

django-facebook-auth can be installed as a normal Python package.

Example instalation for pip::

    $ pip install django-facebook-auth


Configuration
-------------

settings.py
___________

Set USE_TZ = True

Add facebook_auth to INSTALLED_APPS::

    INSTALLED_APPS = (
        ...
        'facebook_auth',
        ...
    )

Add authentication backends to AUTHENTICATION_BACKENDS::

    AUTHENTICATION_BACKENDS = (
        ...
        'facebook_auth.backends.FacebookBackend',
        'facebook_auth.backends.FacebookJavascriptBackend',
        ...
    )

Add task to celery imports::

    CELERY_IMPORTS = (
        "facebook_auth.models",
        ...
    )
