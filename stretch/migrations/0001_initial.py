# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Deploy'
        db.create_table(u'stretch_deploy', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='deploys', to=orm['stretch.Environment'])),
            ('task_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='deploys_to', to=orm['stretch.Release'])),
            ('existing_release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='deploys_from', null=True, to=orm['stretch.Release'])),
        ))
        db.send_create_signal('stretch', ['Deploy'])

        # Adding model 'Environment'
        db.create_table(u'stretch_environment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('system', self.gf('django.db.models.fields.related.ForeignKey')(related_name='environments', to=orm['stretch.System'])),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Release'], null=True)),
        ))
        db.send_create_signal('stretch', ['Environment'])

        # Adding unique constraint on 'Environment', fields ['system', 'name']
        db.create_unique(u'stretch_environment', ['system_id', 'name'])

        # Adding model 'Group'
        db.create_table(u'stretch_group', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='groups', to=orm['stretch.Environment'])),
            ('minimum_nodes', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('maximum_nodes', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(related_name='groups', to=orm['stretch.Node'])),
        ))
        db.send_create_signal('stretch', ['Group'])

        # Adding unique constraint on 'Group', fields ['environment', 'name']
        db.create_unique(u'stretch_group', ['environment_id', 'name'])

        # Adding model 'Host'
        db.create_table(u'stretch_host', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='hosts', to=orm['stretch.Environment'])),
        ))
        db.send_create_signal('stretch', ['Host'])

        # Adding unique constraint on 'Host', fields ['environment', 'name']
        db.create_unique(u'stretch_host', ['environment_id', 'name'])

        # Adding model 'Instance'
        db.create_table(u'stretch_instance', (
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('id', self.gf('uuidfield.fields.UUIDField')(unique=True, max_length=32, primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='instances', to=orm['stretch.Environment'])),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(related_name='instances', to=orm['stretch.Host'])),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(related_name='instances', to=orm['stretch.Node'])),
        ))
        db.send_create_signal('stretch', ['Instance'])

        # Adding model 'Node'
        db.create_table(u'stretch_node', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('system', self.gf('django.db.models.fields.related.ForeignKey')(related_name='nodes', to=orm['stretch.System'])),
        ))
        db.send_create_signal('stretch', ['Node'])

        # Adding unique constraint on 'Node', fields ['system', 'name']
        db.create_unique(u'stretch_node', ['system_id', 'name'])

        # Adding model 'Release'
        db.create_table(u'stretch_release', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('tag', self.gf('django.db.models.fields.TextField')()),
            ('system', self.gf('django.db.models.fields.related.ForeignKey')(related_name='releases', to=orm['stretch.System'])),
        ))
        db.send_create_signal('stretch', ['Release'])

        # Adding unique constraint on 'Release', fields ['system', 'name', 'tag']
        db.create_unique(u'stretch_release', ['system_id', 'name', 'tag'])

        # Adding model 'System'
        db.create_table(u'stretch_system', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')(unique=True)),
        ))
        db.send_create_signal('stretch', ['System'])


    def backwards(self, orm):
        # Removing unique constraint on 'Release', fields ['system', 'name', 'tag']
        db.delete_unique(u'stretch_release', ['system_id', 'name', 'tag'])

        # Removing unique constraint on 'Node', fields ['system', 'name']
        db.delete_unique(u'stretch_node', ['system_id', 'name'])

        # Removing unique constraint on 'Host', fields ['environment', 'name']
        db.delete_unique(u'stretch_host', ['environment_id', 'name'])

        # Removing unique constraint on 'Group', fields ['environment', 'name']
        db.delete_unique(u'stretch_group', ['environment_id', 'name'])

        # Removing unique constraint on 'Environment', fields ['system', 'name']
        db.delete_unique(u'stretch_environment', ['system_id', 'name'])

        # Deleting model 'Deploy'
        db.delete_table(u'stretch_deploy')

        # Deleting model 'Environment'
        db.delete_table(u'stretch_environment')

        # Deleting model 'Group'
        db.delete_table(u'stretch_group')

        # Deleting model 'Host'
        db.delete_table(u'stretch_host')

        # Deleting model 'Instance'
        db.delete_table(u'stretch_instance')

        # Deleting model 'Node'
        db.delete_table(u'stretch_node')

        # Deleting model 'Release'
        db.delete_table(u'stretch_release')

        # Deleting model 'System'
        db.delete_table(u'stretch_system')


    models = {
        'stretch.deploy': {
            'Meta': {'object_name': 'Deploy'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'deploys'", 'to': "orm['stretch.Environment']"}),
            'existing_release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'deploys_from'", 'null': 'True', 'to': "orm['stretch.Release']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'deploys_to'", 'to': "orm['stretch.Release']"}),
            'task_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        'stretch.environment': {
            'Meta': {'unique_together': "(('system', 'name'),)", 'object_name': 'Environment'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['stretch.Release']", 'null': 'True'}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': "orm['stretch.System']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        'stretch.group': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Group'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'groups'", 'to': "orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maximum_nodes': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'minimum_nodes': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'groups'", 'to': "orm['stretch.Node']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        'stretch.host': {
            'Meta': {'unique_together': "(('environment', 'name'),)", 'object_name': 'Host'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'hosts'", 'to': "orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        'stretch.instance': {
            'Meta': {'object_name': 'Instance'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'instances'", 'to': "orm['stretch.Environment']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'instances'", 'to': "orm['stretch.Host']"}),
            'id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'instances'", 'to': "orm['stretch.Node']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        'stretch.node': {
            'Meta': {'unique_together': "(('system', 'name'),)", 'object_name': 'Node'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nodes'", 'to': "orm['stretch.System']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        'stretch.release': {
            'Meta': {'unique_together': "(('system', 'name', 'tag'),)", 'object_name': 'Release'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['stretch.System']"}),
            'tag': ('django.db.models.fields.TextField', [], {}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        'stretch.system': {
            'Meta': {'object_name': 'System'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stretch']