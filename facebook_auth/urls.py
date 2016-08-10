from views import handler

from django.conf.urls import patterns
from django.conf.urls import url

urlpatterns = patterns('facebook_auth.views',
    url(r'^handler$', handler, name='facebook-auth-handler'),
)
