from django.conf import global_settings
from django.conf.urls.defaults import patterns, include
from package_installer import Package


class FacebookAuthPackage(Package):
    INSTALL_APPS = ('facebook_auth',)

    def install_settings(self, settings):
        super(FacebookAuthPackage, self).install_settings(settings)
        backends = settings.get('AUTHENTICATION_BACKENDS', global_settings.AUTHENTICATION_BACKENDS)
        settings['AUTHENTICATION_BACKENDS'] = backends + (
            'facebook_auth.backends.FacebookBackend',
            'facebook_auth.backends.FacebookJavascriptBackend',
        )

PACKAGE = FacebookAuthPackage()
