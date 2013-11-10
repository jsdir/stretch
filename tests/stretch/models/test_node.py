from mock import Mock, patch
from nose.tools import eq_

from stretch.testutils import patch_settings
from stretch.models import Node


@patch('stretch.models.Node.system', Mock())
def test_node_get_image():
    node = Node(name='node')
    node.system = Mock()
    node.system.pk = 1

    eq_(node.get_image(local=True), 'stretch_agent/sys1/node')

    with patch_settings('STRETCH_REGISTRY_PRIVATE_URL', 'private_url'):
        eq_(node.get_image(local=False, private=True), 'private_url/sys1/node')

    with patch_settings('STRETCH_REGISTRY_PUBLIC_URL', 'public_url'):
        eq_(node.get_image(local=False, private=False), 'public_url/sys1/node')
