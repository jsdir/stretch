# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Environment'
        db.create_table(u'api_environment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('promotes_to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
            ('entrypoint', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'api', ['Environment'])

        # Adding model 'Group'
        db.create_table(u'api_group', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
            ('minimum_nodes', self.gf('django.db.models.fields.IntegerField')()),
            ('maximum_nodes', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'api', ['Group'])

        # Adding model 'Node'
        db.create_table(u'api_node', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Group'])),
        ))
        db.send_create_signal(u'api', ['Node'])

        # Adding model 'Trigger'
        db.create_table(u'api_trigger', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
        ))
        db.send_create_signal(u'api', ['Trigger'])

        # Adding model 'Action'
        db.create_table(u'api_action', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trigger', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['api.Trigger'], unique=True)),
        ))
        db.send_create_signal(u'api', ['Action'])

        # Adding model 'Event'
        db.create_table(u'api_event', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trigger', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['api.Trigger'], unique=True)),
        ))
        db.send_create_signal(u'api', ['Event'])

        # Adding model 'Metric'
        db.create_table(u'api_metric', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
        ))
        db.send_create_signal(u'api', ['Metric'])

        # Adding model 'Promotion'
        db.create_table(u'api_promotion', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['api.Environment'])),
        ))
        db.send_create_signal(u'api', ['Promotion'])


    def backwards(self, orm):
        # Deleting model 'Environment'
        db.delete_table(u'api_environment')

        # Deleting model 'Group'
        db.delete_table(u'api_group')

        # Deleting model 'Node'
        db.delete_table(u'api_node')

        # Deleting model 'Trigger'
        db.delete_table(u'api_trigger')

        # Deleting model 'Action'
        db.delete_table(u'api_action')

        # Deleting model 'Event'
        db.delete_table(u'api_event')

        # Deleting model 'Metric'
        db.delete_table(u'api_metric')

        # Deleting model 'Promotion'
        db.delete_table(u'api_promotion')


    models = {
        u'api.action': {
            'Meta': {'object_name': 'Action'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trigger': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['api.Trigger']", 'unique': 'True'})
        },
        u'api.environment': {
            'Meta': {'object_name': 'Environment'},
            'entrypoint': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'promotes_to': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"})
        },
        u'api.event': {
            'Meta': {'object_name': 'Event'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trigger': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['api.Trigger']", 'unique': 'True'})
        },
        u'api.group': {
            'Meta': {'object_name': 'Group'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maximum_nodes': ('django.db.models.fields.IntegerField', [], {}),
            'minimum_nodes': ('django.db.models.fields.IntegerField', [], {}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'})
        },
        u'api.metric': {
            'Meta': {'object_name': 'Metric'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'api.node': {
            'Meta': {'object_name': 'Node'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'api.promotion': {
            'Meta': {'object_name': 'Promotion'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'api.trigger': {
            'Meta': {'object_name': 'Trigger'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['api.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['api']