#!/bin/bash -e

bash -c "createdb facebook_auth-test-database || true"
rm -rf reports reports3.3
virtualenv .env
. .env/bin/activate
pip install -e .
pip install psycopg2 django-jenkins==0.14.1 pylint coverage pep8 pyflakes factory_boy==2.0.2 django-celery==3.0.23 mock

python runtests.py legacy
deactivate


virtualenv .env3.3 --python=python3.3
. .env3.3/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)
pip install django==1.6 psycopg2 django-jenkins pylint coverage pep8 pyflakes factory_boy django-celery facepy
python runtests.py
