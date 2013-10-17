# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Service.created_at'
        db.add_column(u'stretch_service', 'created_at',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True, blank=True),
                      keep_default=False)

        # Adding field 'Service.updated_at'
        db.add_column(u'stretch_service', 'updated_at',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True, blank=True),
                      keep_default=False)


        # Changing field 'Environment.created_at'
        db.alter_column(u'stretch_environment', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Environment.updated_at'
        db.alter_column(u'stretch_environment', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'PortBinding.created_at'
        db.alter_column(u'stretch_portbinding', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'PortBinding.updated_at'
        db.alter_column(u'stretch_portbinding', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'Release.created_at'
        db.alter_column(u'stretch_release', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Release.updated_at'
        db.alter_column(u'stretch_release', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'Instance.created_at'
        db.alter_column(u'stretch_instance', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Instance.updated_at'
        db.alter_column(u'stretch_instance', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'System.updated_at'
        db.alter_column(u'stretch_system', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'System.created_at'
        db.alter_column(u'stretch_system', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Node.updated_at'
        db.alter_column(u'stretch_node', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'Node.created_at'
        db.alter_column(u'stretch_node', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Deploy.task_id'
        db.alter_column(u'stretch_deploy', 'task_id', self.gf('django.db.models.fields.CharField')(max_length=128, null=True))

        # Changing field 'Deploy.created_at'
        db.alter_column(u'stretch_deploy', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Deploy.updated_at'
        db.alter_column(u'stretch_deploy', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'Group.created_at'
        db.alter_column(u'stretch_group', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Group.updated_at'
        db.alter_column(u'stretch_group', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

        # Changing field 'Host.created_at'
        db.alter_column(u'stretch_host', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, null=True))

        # Changing field 'Host.updated_at'
        db.alter_column(u'stretch_host', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, null=True))

    def backwards(self, orm):
        # Deleting field 'Service.created_at'
        db.delete_column(u'stretch_service', 'created_at')

        # Deleting field 'Service.updated_at'
        db.delete_column(u'stretch_service', 'updated_at')


        # User chose to not deal with backwards NULL issues for 'Environment.created_at'
        raise RuntimeError("Cannot reverse this migration. 'Environment.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Environment.created_at'
        db.alter_column(u'stretch_environment', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Environment.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'Environment.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Environment.updated_at'
        db.alter_column(u'stretch_environment', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'PortBinding.created_at'
        raise RuntimeError("Cannot reverse this migration. 'PortBinding.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'PortBinding.created_at'
        db.alter_column(u'stretch_portbinding', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'PortBinding.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'PortBinding.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'PortBinding.updated_at'
        db.alter_column(u'stretch_portbinding', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'Release.created_at'
        raise RuntimeError("Cannot reverse this migration. 'Release.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Release.created_at'
        db.alter_column(u'stretch_release', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Release.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'Release.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Release.updated_at'
        db.alter_column(u'stretch_release', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'Instance.created_at'
        raise RuntimeError("Cannot reverse this migration. 'Instance.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Instance.created_at'
        db.alter_column(u'stretch_instance', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Instance.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'Instance.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Instance.updated_at'
        db.alter_column(u'stretch_instance', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'System.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'System.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'System.updated_at'
        db.alter_column(u'stretch_system', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'System.created_at'
        raise RuntimeError("Cannot reverse this migration. 'System.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'System.created_at'
        db.alter_column(u'stretch_system', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Node.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'Node.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Node.updated_at'
        db.alter_column(u'stretch_node', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'Node.created_at'
        raise RuntimeError("Cannot reverse this migration. 'Node.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Node.created_at'
        db.alter_column(u'stretch_node', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Deploy.task_id'
        raise RuntimeError("Cannot reverse this migration. 'Deploy.task_id' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Deploy.task_id'
        db.alter_column(u'stretch_deploy', 'task_id', self.gf('django.db.models.fields.CharField')(max_length=128))

        # User chose to not deal with backwards NULL issues for 'Deploy.created_at'
        raise RuntimeError("Cannot reverse this migration. 'Deploy.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Deploy.created_at'
        db.alter_column(u'stretch_deploy', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Deploy.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'Deploy.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Deploy.updated_at'
        db.alter_column(u'stretch_deploy', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'Group.created_at'
        raise RuntimeError("Cannot reverse this migration. 'Group.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Group.created_at'
        db.alter_column(u'stretch_group', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Group.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'Group.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Group.updated_at'
        db.alter_column(u'stretch_group', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

        # User chose to not deal with backwards NULL issues for 'Host.created_at'
        raise RuntimeError("Cannot reverse this migration. 'Host.created_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Host.created_at'
        db.alter_column(u'stretch_host', 'created_at', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True))

        # User chose to not deal with backwards NULL issues for 'Host.updated_at'
        raise RuntimeError("Cannot reverse this migration. 'Host.updated_at' and its values cannot be restored.")
        
        # The following code is provided here to aid in writing a correct migration
        # Changing field 'Host.updated_at'
        db.alter_column(u'stretch_host', 'updated_at', self.gf('django.db.models.fields.DateTimeField')(auto_now=True))

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
            'auto_deploy': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
            'load_balancer': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['stretch.LoadBalancer']", 'unique': 'True', 'null': 'True'}),
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
            'domain_name': ('django.db.models.fields.TextField', [], {}),
            'environment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'hosts'", 'to': u"orm['stretch.Environment']"}),
            'fqdn': ('django.db.models.fields.TextField', [], {'unique': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'hosts'", 'null': 'True', 'to': u"orm['stretch.Group']"}),
            'hostname': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
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
            'address': ('django.db.models.fields.GenericIPAddressField', [], {'max_length': '39'}),
            'backend_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'}),
            'host_port': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'port': ('django.db.models.fields.IntegerField', [], {}),
            'protocol': ('django.db.models.fields.TextField', [], {})
        },
        u'stretch.node': {
            'Meta': {'object_name': 'Node'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'ports': ('jsonfield.fields.JSONField', [], {}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'nodes'", 'to': u"orm['stretch.System']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.portbinding': {
            'Meta': {'object_name': 'PortBinding'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'destination': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'instance': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'port_bindings'", 'to': u"orm['stretch.Instance']"}),
            'source': ('django.db.models.fields.IntegerField', [], {}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.release': {
            'Meta': {'object_name': 'Release'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'sha': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': u"orm['stretch.System']"}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'stretch.service': {
            'Meta': {'object_name': 'Service'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'data': ('jsonfield.fields.JSONField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {}),
            'system': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'services'", 'to': u"orm['stretch.System']"}),
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