# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FacebookUser',
            fields=[
                ('user_ptr', models.OneToOneField(serialize=False, primary_key=True, to=settings.AUTH_USER_MODEL, auto_created=True)),
                ('user_id', models.BigIntegerField(unique=True)),
                ('scope', models.CharField(default='', max_length=512, blank=True)),
                ('app_friends', models.ManyToManyField(to='facebook_auth.FacebookUser')),
            ],
            options={
                'verbose_name': 'user',
                'abstract': False,
                'verbose_name_plural': 'users',
            },
            bases=('auth.user',),
        ),
        migrations.CreateModel(
            name='UserToken',
            fields=[
                ('id', models.AutoField(serialize=False, verbose_name='ID', auto_created=True, primary_key=True)),
                ('provider_user_id', models.CharField(max_length=255)),
                ('token', models.TextField(unique=True)),
                ('granted_at', models.DateTimeField(auto_now_add=True)),
                ('expiration_date', models.DateTimeField(default=None, null=True, blank=True)),
                ('deleted', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'User token',
                'verbose_name_plural': 'User tokens',
            },
            bases=(models.Model,),
        ),
    ]
