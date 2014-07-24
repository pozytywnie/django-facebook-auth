# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('facebook_auth', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='facebookuser',
            name='app_friends',
            field=models.ManyToManyField(to='facebook_auth.FacebookUser'),
            preserve_default=True,
        ),
    ]
