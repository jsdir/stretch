# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'System'
        db.create_table(u'stretch_system', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('domain_name', self.gf('django.db.models.fields.TextField')(unique=True, null=True)),
        ))
        db.send_create_signal(u'stretch', ['System'])

        # Adding model 'Environment'
        db.create_table(u'stretch_environment', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('auto_deploy', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('system', self.gf('django.db.models.fields.related.ForeignKey')(related_name='environments', to=orm['stretch.System'])),
            ('current_release', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Release'], null=True)),
            ('using_source', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('config', self.gf('jsonfield.fields.JSONField')(default={})),
            ('app_paths', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'stretch', ['Environment'])

        # Adding model 'Release'
        db.create_table(u'stretch_release', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('sha', self.gf('django.db.models.fields.CharField')(max_length=28)),
            ('system', self.gf('django.db.models.fields.related.ForeignKey')(related_name='releases', to=orm['stretch.System'])),
        ))
        db.send_create_signal(u'stretch', ['Release'])

        # Adding model 'Port'
        db.create_table(u'stretch_port', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(related_name='ports', to=orm['stretch.Node'])),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('number', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal(u'stretch', ['Port'])

        # Adding model 'Node'
        db.create_table(u'stretch_node', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('system', self.gf('django.db.models.fields.related.ForeignKey')(related_name='nodes', to=orm['stretch.System'])),
        ))
        db.send_create_signal(u'stretch', ['Node'])

        # Adding model 'Instance'
        db.create_table(u'stretch_instance', (
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('id', self.gf('uuidfield.fields.UUIDField')(unique=True, max_length=32, primary_key=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='instances', to=orm['stretch.Environment'])),
            ('host', self.gf('django.db.models.fields.related.ForeignKey')(related_name='instances', to=orm['stretch.Host'])),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(related_name='instances', to=orm['stretch.Node'])),
        ))
        db.send_create_signal(u'stretch', ['Instance'])

        # Adding model 'LoadBalancer'
        db.create_table(u'stretch_loadbalancer', (
            ('id', self.gf('uuidfield.fields.UUIDField')(max_length=32, primary_key=True)),
            ('port_name', self.gf('django.db.models.fields.TextField')()),
            ('protocol', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('options', self.gf('jsonfield.fields.JSONField')(default={})),
        ))
        db.send_create_signal(u'stretch', ['LoadBalancer'])

        # Adding model 'Host'
        db.create_table(u'stretch_host', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('fqdn', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('name', self.gf('django.db.models.fields.TextField')(unique=True)),
            ('hostname', self.gf('django.db.models.fields.TextField')()),
            ('domain_name', self.gf('django.db.models.fields.TextField')(null=True)),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='hosts', to=orm['stretch.Environment'])),
            ('address', self.gf('django.db.models.fields.GenericIPAddressField')(max_length=39)),
        ))
        db.send_create_signal(u'stretch', ['Host'])

        # Adding model 'Group'
        db.create_table(u'stretch_group', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.TextField')()),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='groups', to=orm['stretch.Environment'])),
            ('minimum_nodes', self.gf('django.db.models.fields.IntegerField')(default=1)),
            ('maximum_nodes', self.gf('django.db.models.fields.IntegerField')(null=True)),
            ('node', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['stretch.Node'])),
            ('load_balancer', self.gf('django.db.models.fields.related.OneToOneField')(related_name='group', unique=True, null=True, to=orm['stretch.LoadBalancer'])),
        ))
        db.send_create_signal(u'stretch', ['Group'])

        # Adding model 'Deploy'
        db.create_table(u'stretch_deploy', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True)),
            ('updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True)),
            ('release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='deploy_releases', null=True, to=orm['stretch.Release'])),
            ('existing_release', self.gf('django.db.models.fields.related.ForeignKey')(related_name='deploy_existing_releases', null=True, to=orm['stretch.Release'])),
            ('environment', self.gf('django.db.models.fields.related.ForeignKey')(related_name='deploys', to=orm['stretch.Environment'])),
            ('task_id', self.gf('django.db.models.fields.CharField')(max_length=128, null=True)),
        ))
        db.send_create_signal(u'stretch', ['Deploy'])


    def backwards(self, orm):
        # Deleting model 'System'
        db.delete_table(u'stretch_system')

        # Deleting model 'Environment'
        db.delete_table(u'stretch_environment')

        # Deleting model 'Release'
        db.delete_table(u'stretch_release')

        # Deleting model 'Port'
        db.delete_table(u'stretch_port')

        # Deleting model 'Node'
        db.delete_table(u'stretch_node')

        # Deleting model 'Instance'
        db.delete_table(u'stretch_instance')

        # Deleting model 'LoadBalancer'
        db.delete_table(u'stretch_loadbalancer')

        # Deleting model 'Host'
        db.delete_table(u'stretch_host')

        # Deleting model 'Group'
        db.delete_table(u'stretch_group')

        # Deleting model 'Deploy'
        db.delete_table(u'stretch_deploy')


    models = {
        u'stretch.deploy': {
            'Meta': {'object_name': 'Deploy'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'deploys'", 'to': u"orm['stretch.Environment']"}),
            'existing_release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'deploy_existing_releases'", 'null': 'True', 'to': u"orm['stretch.Release']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'release': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'deploy_releases'", 'null': 'True', 'to': u"orm['stretch.Release']"}),
            'task_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.environment': {
            'Meta': {'object_name': 'Environment'},
            'app_paths': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'auto_deploy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'config': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'current_release': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stretch.Release']", 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'environments'", 'to': u"orm['stretch.System']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'}),
            'using_source': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'stretch.group': {
            'Meta': {'object_name': 'Group'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'groups'", 'to': u"orm['stretch.Environment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'load_balancer': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'group'", 'unique': 'True', 'null': 'True', 'to': u"orm['stretch.LoadBalancer']"}),
            'maximum_nodes': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'minimum_nodes': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['stretch.Node']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.host': {
            'Meta': {'object_name': 'Host'},
            'address': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'hosts'", 'to': u"orm['stretch.Environment']"}),
            'fqdn': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'hostname': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.instance': {
            'Meta': {'object_name': 'Instance'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'instances'", 'to': u"orm['stretch.Environment']"}),
            'host': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'instances'", 'to': u"orm['stretch.Host']"}),
            'id': ('uuidfield.fields.UUIDField', [], {'unique': 'True', 'max_length': '32', 'primary_key': 'True'}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'instances'", 'to': u"orm['stretch.Node']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.loadbalancer': {
            'Meta': {'object_name': 'LoadBalancer'},
            'id': ('uuidfield.fields.UUIDField', [], {'max_length': '32', 'primary_key': 'True'}),
            'options': ('jsonfield.fields.JSONField', [], {'default': '{}'}),
            'port_name': ('django.db.models.fields.TextField', [], {}),
            'protocol': ('django.db.models.fields.CharField', [], {'max_length': '10'})
        },
        u'stretch.node': {
            'Meta': {'object_name': 'Node'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nodes'", 'to': u"orm['stretch.System']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.port': {
            'Meta': {'object_name': 'Port'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'node': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'ports'", 'to': u"orm['stretch.Node']"}),
            'number': ('django.db.models.fields.IntegerField', [], {}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.release': {
            'Meta': {'object_name': 'Release'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '28'}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': u"orm['stretch.System']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.system': {
            'Meta': {'object_name': 'System'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'domain_name': ('django.db.models.fields.TextField', [], {'unique': 'True', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['stretch']