import os
import sys

from django.conf import settings
from django.core.management import execute_manager

if not settings.configured:
    PROJECT_APPS = (
        'facebook_auth',
    )
    settings.configure(
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'facebook_auth-test-database',
            }
        },
        PROJECT_APPS = PROJECT_APPS,
        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.messages',
            'django_jenkins',
        ) + PROJECT_APPS,
        SITE_ID = 1,
        ROOT_URLCONF = 'facebook_auth.urls',
        JENKINS_TASKS = (
            'django_jenkins.tasks.with_coverage',
            'django_jenkins.tasks.django_tests',
            'django_jenkins.tasks.run_pep8',
            'django_jenkins.tasks.run_pyflakes',
        )
    )

sys.argv += ['jenkins']
execute_manager(settings)
