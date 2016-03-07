from django.core.management.base import BaseCommand

from facebook_auth import models


class Command(BaseCommand):
    def handle(self, *args, **options):
        users_ids = (models.UserToken.objects.distinct('provider_user_id')
                     .values_list('provider_user_id', flat=True))
        for user_id in users_ids:
            models.debug_all_tokens_for_user.delay(user_id)
            self.stdout.write('Debugging user "%s"' % user_id)
