from mock import patch
from django.test import TestCase

from stretch import models


class TestGroup(TestCase):

    def setUp(self):
        self.system = models.System(name='sys')
        self.system.save()
        self.env = models.Environment(system=self.system)
        self.env.save()
        self.node = models.Node(name='node_name', system=self.system)
        self.node.save()
        self.group = models.Group(
            name='group',
            environment=self.env,
            minimum_nodes=0,
            maximum_nodes=10,
            node = self.node
        )
        self.group.save()

    def create_host(self, i, group):
        host = models.Host(name=str(i), environment=self.env)
        host.group = group
        host.save()

    @patch('stretch.models.group.Group._create_host')
    def test_scale_up(self, _create_host):
        self.group.maximum_nodes = 3
        self.group.scale_up(3)

        self.assertEquals(self.group._create_host.s.call_count, 3)

        self.group._create_host.reset_mock()
        [self.create_host(i, self.group) for i in xrange(3)]

        with self.assertRaises(models.group.ScaleException):
            self.group.scale_up(1)

        assert not self.group._create_host.s.called

    @patch('stretch.models.group.Group._delete_host')
    def test_scale_down(self, _delete_host):
        [self.create_host(i, self.group) for i in xrange(4)]

        self.group.minimum_nodes = 2
        self.group.scale_down(2)

        self.assertEquals(self.group._delete_host.s.call_count, 2)

        self.group._delete_host.reset_mock()
        hosts = self.group.hosts.all()
        hosts[0].delete()
        hosts[1].delete()

        with self.assertRaises(models.group.ScaleException):
            self.group.scale_down(1)

        assert not self.group._delete_host.s.called

    @patch('stretch.models.group.Group.scale_up')
    @patch('stretch.models.group.Group.scale_down')
    def test_scale_to(self, scale_down, scale_up):
        self.group.scale_to(0)
        assert not self.group.scale_down.called
        assert not self.group.scale_up.called
        self.create_host(1, self.group)
        self.group.scale_to(3)
        self.group.scale_up.assert_called_with(2)
        self.create_host(2, self.group)
        self.create_host(3, self.group)
        self.group.scale_to(0)
        self.group.scale_down.assert_called_with(3)
