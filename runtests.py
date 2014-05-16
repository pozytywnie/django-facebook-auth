import sys

from django.conf import settings
from django.core.management import execute_from_command_line
import djcelery

LEGACY = len(sys.argv) == 2 and sys.argv[1] == 'legacy'
OUTPUT_DIR = 'reports' if LEGACY else 'reports3.3'

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
        USE_TZ = True,
        BROKER_URL = 'django://',
        PROJECT_APPS = PROJECT_APPS,
        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.sessions',
            'django.contrib.sites',
            'django.contrib.messages',
            'djcelery',
            'kombu.transport.django',
        ) + PROJECT_APPS,
        SITE_ID = 1,
        ROOT_URLCONF = 'facebook_auth.urls',
    )

djcelery.setup_loader()
execute_from_command_line(['runtests.py', 'test'])
