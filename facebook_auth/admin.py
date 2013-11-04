from django.contrib import admin

from facebook_auth import models


class UserTokenAdmin(admin.ModelAdmin):
    list_display = ('provider_user_id', 'expiration_date', 'deleted')
    list_filter = ('deleted',)
    search_fields = ('token', 'provider_user_id')


admin.site.register(models.UserToken, UserTokenAdmin)
