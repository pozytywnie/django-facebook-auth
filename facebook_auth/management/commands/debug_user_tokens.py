from django.core.management.base import BaseCommand

from facebook_auth import models


class Command(BaseCommand):
    def handle(self, *args, **options):
        users = (models.UserToken.objects.distinct('provider_user_id')
                 .values_list('provider_user_id', flat=True))
        for user in users:
            models.debug_all_tokens_for_user.delay(user)
            self.stdout.write('Debugging user "%s"' % user)
