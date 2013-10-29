from __future__ import absolute_import
import os
import imp
from mock import patch, Mock, DEFAULT, call

import stretch
from stretch.testutils import mock_attr


dir_name = os.path.split(stretch.__file__)[0]
module = os.path.join(dir_name, '../lib/salt/modules/stretch.py')
stretch = imp.load_source('stretch', module)


@patch.multiple(stretch, Instance=DEFAULT, db=DEFAULT)
def test_main(Instance, db):
    mocks = [Mock(), Mock()]
    Instance.side_effect = mocks
    db.instances.find.return_value = [{'id':'1'}, {'id':'2'}]
    stretch.main()
    mocks[0].start.assert_called_with()
    mocks[1].start.assert_called_with()
    Instance.assert_has_calls([call('1'), call('2')], any_order=True)
