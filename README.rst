django-facebook-auth
========================

.. image:: https://travis-ci.org/pozytywnie/django-facebook-auth.svg
   :target: https://travis-ci.org/pozytywnie/django-facebook-auth

A stable Facebook authentication backend for Django >= 1.4.

Starting from version 3.6.0 Django 1.7 is supported. South migrations are move to south_migrations so you need South 1.0 or newer to use them.

Requires Celery for background token operations.


Installation
------------

Package
_______

django-facebook-auth can be installed as a normal Python package.

Example installation for pip::

    $ pip install django-facebook-auth


Configuration
-------------

Celery
______

This project requires working Celery integration. In case you are new to
Celery, the `First steps with Django tutorial
<http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html>`_
will help you to hit the ground running.


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

Set necessary Facebook properties::

    FACEBOOK_CANVAS_URL = 'http://pozytywnie.pl/'  # root of your domain
    FACEBOOK_APP_ID = '1234567890'
    FACEBOOK_APP_SECRET = '91162629d258a876ee994e9233b2ad87'


Usage
-----

The authentication flow is very straightforward:

1.  Redirect your user to Facebook OAuth endpoint using redirect_uri prepared
    with the help of this library.

    First in your view or context processor prepare the necessary parameters
    for the Facebook OAuth endpoint::

        from facebook_auth.urls import redirect_uri

        def login(request):
            ...
            context.update({
                'redirect_uri': redirect_uri('/login/success', '/login/fail'),
                'client_id': settings.FACEBOOK_APP_ID,
                'scope': 'email'
            })
            ...

    And embed the link in your template::

        <a href="https://www.facebook.com/dialog/oauth?client_id={{ client_id }}&amp;scope={{ scope }}&amp;redirect_uri={{ redirect_uri }}">Login using Facebook</a>

2.  User is redirected back to django-facebook-auth authentication handler,
    which either authenticates the user or refuses to do so.

    Prepare a separate view for each scenario.

3.  A best token for authenticated user is negotiated with Facebook in the
    background, using your Celery worker.
