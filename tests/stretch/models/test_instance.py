from mock import Mock, patch
from unittest import TestCase

from stretch.testutils import patch_settings
from stretch.models import Instance


class TestInstance(TestCase):
    def setUp(self):
        self.instance = Instance(name='name', sha='sha')

    @patch('stretch.models.Instance.host.agent')
    def test_pre_delete(self, agent):
        raise Exception
        pass
        """
        env = Mock()
        config_manager = env.system.config_manager
        self.env.post_save(Mock(), env, False)
        config_manager.sync_env_config.assert_called_with(env)
        """
