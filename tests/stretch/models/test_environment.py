from mock import patch, call
from django.test import TestCase
from django.test.utils import override_settings

from stretch.models import System, Environment, Release, Node


class TestEnvironment(TestCase):

    def setUp(self):
        self.system = System(name='sys')
        self.env = Environment(name='env', system=self.system)

    @patch('stretch.models.environment.Deploy')
    @patch('stretch.models.environment.current_task', 'task')
    @override_settings(CELERY_ALWAYS_EAGER=True)
    def test_deploy(self, deploy):
        node1 = Node(name='node1', system=self.system)
        node1.env = self.env
        node2 = Node(name='node2', system=self.system)
        node2.env = self.env
        release = Release()

        self.env.deploy.apply([release]).get()
        self.env.deploy.apply([release]).get()

        deploy.create.assert_has_calls([call(self.env, release, 'task')])
        self.assertEquals(self.env.release, release)
