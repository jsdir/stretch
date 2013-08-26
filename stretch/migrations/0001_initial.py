# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Environment'
        db.create_table(u'stretch_environment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
        ))
        db.send_create_signal(u'stretch', ['Environment'])

        # Adding model 'Node'
        db.create_table(u'stretch_node', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Environment'])),
        ))
        db.send_create_signal(u'stretch', ['Node'])

        # Adding model 'Group'
        db.create_table(u'stretch_group', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Environment'])),
        ))
        db.send_create_signal(u'stretch', ['Group'])

        # Adding model 'Trigger'
        db.create_table(u'stretch_trigger', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Environment'])),
        ))
        db.send_create_signal(u'stretch', ['Trigger'])

        # Adding model 'Action'
        db.create_table(u'stretch_action', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trigger', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['stretch.Trigger'], unique=True)),
        ))
        db.send_create_signal(u'stretch', ['Action'])

        # Adding model 'Event'
        db.create_table(u'stretch_event', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('trigger', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['stretch.Trigger'], unique=True)),
        ))
        db.send_create_signal(u'stretch', ['Event'])

        # Adding model 'Metric'
        db.create_table(u'stretch_metric', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Environment'])),
        ))
        db.send_create_signal(u'stretch', ['Metric'])

        # Adding model 'Promotion'
        db.create_table(u'stretch_promotion', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Environment'])),
        ))
        db.send_create_signal(u'stretch', ['Promotion'])


    def backwards(self, orm):
        # Deleting model 'Environment'
        db.delete_table(u'stretch_environment')

        # Deleting model 'Node'
        db.delete_table(u'stretch_node')

        # Deleting model 'Group'
        db.delete_table(u'stretch_group')

        # Deleting model 'Trigger'
        db.delete_table(u'stretch_trigger')

        # Deleting model 'Action'
        db.delete_table(u'stretch_action')

        # Deleting model 'Event'
        db.delete_table(u'stretch_event')

        # Deleting model 'Metric'
        db.delete_table(u'stretch_metric')

        # Deleting model 'Promotion'
        db.delete_table(u'stretch_promotion')


    models = {
        u'stretch.action': {
            'Meta': {'object_name': 'Action'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trigger': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['stretch.Trigger']", 'unique': 'True'})
        },
        u'stretch.environment': {
            'Meta': {'object_name': 'Environment'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'})
        },
        u'stretch.event': {
            'Meta': {'object_name': 'Event'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'trigger': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['stretch.Trigger']", 'unique': 'True'})
        },
        u'stretch.group': {
            'Meta': {'object_name': 'Group'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'stretch.metric': {
            'Meta': {'object_name': 'Metric'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'stretch.node': {
            'Meta': {'object_name': 'Node'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'stretch.promotion': {
            'Meta': {'object_name': 'Promotion'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'stretch.trigger': {
            'Meta': {'object_name': 'Trigger'},
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['stretch']