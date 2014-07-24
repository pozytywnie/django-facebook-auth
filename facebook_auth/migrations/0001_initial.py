# encoding: utf8
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('provider_user_id', models.CharField(max_length=255)),
                ('token', models.TextField(unique=True)),
                ('expiration_date', models.DateTimeField()),
                ('deleted', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'User token',
                'verbose_name_plural': 'User tokens',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FacebookUser',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, primary_key=True, to_field='id', serialize=False, to=settings.AUTH_USER_MODEL)),
                ('user_id', models.BigIntegerField(unique=True)),
                ('scope', models.CharField(blank=True, max_length=512, default='')),
            ],
            options={
                'verbose_name': 'user',
                'abstract': False,
                'verbose_name_plural': 'users',
            },
            bases=('auth.user',),
        ),
    ]
