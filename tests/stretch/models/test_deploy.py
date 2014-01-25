from mock import Mock, patch, call
from twisted.internet import defer
from django.test import TestCase
from contextlib import contextmanager
from django.test.utils import override_settings

from stretch import models, testutils


class TestDeploy(TestCase):

    # SQLite's in-memory database cannot be shared between threads.

    def setUp(self):
        self.system = models.System(name='sys')
        self.system.save()
        self.env = models.Environment(name='env', system=self.system)
        self.env.save()

    @patch('stretch.models.host.Host.agent')
    @patch('stretch.models.host.Host.instances')
    @patch('stretch.models.environment.Environment.hosts')
    @override_settings(STRETCH_DEPLOY_BATCH_SIZE=2)
    def test_deploy_run(self, hosts, instances, agent):
        host = models.Host()
        instance = models.Instance()
        instances.all.return_value = [instance]
        d = defer.Deferred()
        d.callback(None)
        agent.pull_nodes.return_value = d
        hosts.all.return_value = [host]
        # Setup objects
        current_task = Mock()
        current_task.request.id = 'task-id'

        node1 = models.Node(name='node1', system=self.system)
        node1.env = self.env
        node1.save()
        node2 = models.Node(name='node2', system=self.system)
        node2.env = self.env
        node2.save()

        snapshot = Mock()
        @contextmanager
        def snapshot_context():
            yield snapshot

        release = models.Release(system=self.system)
        release.save()
        release.get_snapshot = snapshot_context

        deploy = models.Deploy.create(self.env, release, current_task)

        # Run deploy
        deploy.run()

        # Object assertions
        self.assertEquals(deploy.task_id, 'task-id')

        # Snapshot assertions
        snapshot.run_task.assert_has_calls([call('before_deploy', release),
                                            call('after_deploy', release)])
        snapshot.build.assert_called_with(release, {'node1': 1, 'node2': 2})
