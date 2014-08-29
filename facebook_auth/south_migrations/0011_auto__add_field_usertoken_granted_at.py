# -*- coding: utf-8 -*-
from south.db import db
from south.v2 import SchemaMigration
from django.utils import timezone


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'UserToken.granted_at'
        db.add_column('facebook_auth_usertoken', 'granted_at',
                      self.gf('django.db.models.fields.DateTimeField')(blank=True, auto_now_add=True, default=timezone.now),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'UserToken.granted_at'
        db.delete_column('facebook_auth_usertoken', 'granted_at')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'unique': 'True'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True', 'symmetrical': 'False'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'blank': 'True', 'max_length': '75'}),
            'first_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'related_name': "'user_set'", 'blank': 'True', 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'blank': 'True', 'max_length': '30'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'related_name': "'user_set'", 'blank': 'True', 'symmetrical': 'False'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '30', 'unique': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'ordering': "('name',)", 'db_table': "'django_content_type'", 'object_name': 'ContentType'},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'facebook_auth.facebookuser': {
            'Meta': {'_ormbases': ['auth.User'], 'object_name': 'FacebookUser'},
            'app_friends': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['facebook_auth.FacebookUser']", 'related_name': "'app_friends_rel_+'"}),
            'scope': ('django.db.models.fields.CharField', [], {'blank': 'True', 'default': "''", 'max_length': '512'}),
            'user_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'user_ptr': ('django.db.models.fields.related.OneToOneField', [], {'primary_key': 'True', 'to': "orm['auth.User']", 'unique': 'True'})
        },
        'facebook_auth.usertoken': {
            'Meta': {'object_name': 'UserToken'},
            'deleted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {}),
            'granted_at': ('django.db.models.fields.DateTimeField', [], {'blank': 'True', 'auto_now_add': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'provider_user_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'token': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        }
    }

    complete_apps = ['facebook_auth']
