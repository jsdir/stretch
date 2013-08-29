# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Metric'
        db.delete_table(u'api_metric')

        # Deleting model 'Action'
        db.delete_table(u'api_action')

        # Deleting model 'Promotion'
        db.delete_table(u'api_promotion')

        # Deleting model 'Trigger'
        db.delete_table(u'api_trigger')

        # Deleting model 'Event'
        db.delete_table(u'api_event')

        # Adding model 'Deploy'
        db.create_table(u'api_deploy', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Release'])),
            ('target', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
            ('state', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
        ))
        db.send_create_signal(u'api', ['Deploy'])

        # Adding model 'Release'
        db.create_table(u'api_release', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ref', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal(u'api', ['Release'])

        # Deleting field 'Environment.promotes_to'
        db.delete_column(u'api_environment', 'promotes_to_id')

        # Deleting field 'Environment.entrypoint'
        db.delete_column(u'api_environment', 'entrypoint')


    def backwards(self, orm):
        # Adding model 'Metric'
        db.create_table(u'api_metric', (
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'api', ['Metric'])

        # Adding model 'Action'
        db.create_table(u'api_action', (
            ('trigger', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['api.Trigger'], unique=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'api', ['Action'])

        # Adding model 'Promotion'
        db.create_table(u'api_promotion', (
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'api', ['Promotion'])

        # Adding model 'Trigger'
        db.create_table(u'api_trigger', (
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'api', ['Trigger'])

        # Adding model 'Event'
        db.create_table(u'api_event', (
            ('trigger', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['api.Trigger'], unique=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal(u'api', ['Event'])

        # Deleting model 'Deploy'
        db.delete_table(u'api_deploy')

        # Deleting model 'Release'
        db.delete_table(u'api_release')


        # User chose to not deal with backwards NULL issues for 'Environment.promotes_to'
        raise RuntimeError("Cannot reverse this migration. 'Environment.promotes_to' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration        # Adding field 'Environment.promotes_to'
        db.add_column(u'api_environment', 'promotes_to',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment']),
                      keep_default=False)

        # Adding field 'Environment.entrypoint'
        db.add_column(u'api_environment', 'entrypoint',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


    models = {
        u'api.deploy': {
            'Meta': {'object_name': 'Deploy'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Release']"}),
            'state': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"})
        },
        u'api.environment': {
            'Meta': {'object_name': 'Environment'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        u'api.group': {
            'Meta': {'object_name': 'Group'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maximum_nodes': ('django.db.models.fields.IntegerField', [], {'default': '-1'}),
            'minimum_nodes': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        u'api.node': {
            'Meta': {'object_name': 'Node'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'api.release': {
            'Meta': {'object_name': 'Release'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ref': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['api']