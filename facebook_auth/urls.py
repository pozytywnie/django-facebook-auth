from facebook_auth.views import handler

from django.conf.urls import url

urlpatterns = (
    url(r'^handler$', handler, name='facebook-auth-handler'),
)
