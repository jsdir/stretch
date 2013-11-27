from mock import Mock, patch
from nose.tools import eq_

from stretch.testutils import patch_settings
from stretch.models import Node
from stretch.utils import UrlLocation


@patch('stretch.models.Node.system', Mock())
def test_node_get_image():
    node = Node(name='node')
    node.system = Mock()
    node.system.pk = 1

    eq_(node.get_image(local=True), 'stretch_agent/sys1/node')

    location = UrlLocation('public_url', private='private_url')

    with patch_settings('STRETCH_REGISTRY', location):
        eq_(node.get_image(local=False, private=True), 'private_url/sys1/node')
        eq_(node.get_image(local=False, private=False), 'public_url/sys1/node')
