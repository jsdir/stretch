from mock import Mock, patch
from unittest import TestCase

from stretch import models


class TestHost(TestCase):
    def setUp(self):
        # self.env = Mock()
        self.host = models.Host()

    @patch('stretch.models.Host.environment')
    @patch('stretch.models.Instance', create=True)
    def test_create_instance(self, Instance, env):
        node = Mock()
        self.host.create_instance(node)
        Instance.create.assert_called_with(env, self.host, node)
