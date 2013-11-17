from nose.tools import assert_in

from stretch import testutils
from stretch.agent import api


class TestApi(testutils.AgentTestCase):
    def test_index(self):
        assert_in('stretch-agent', self.client.get('/').data)
