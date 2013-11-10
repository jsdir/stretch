from mock import Mock, patch
from unittest import TestCase

from stretch.testutils import patch_settings
from stretch.models import Release


class TestRelease(TestCase):
    def setUp(self):
        self.release = Release(name='name', sha='sha')

    @patch_settings('STRETCH_DATA_DIR', '/stretch')
    def test_data_dir(self):
        self.assertEquals(self.release.data_dir, '/stretch/releases/sha')

    @patch('stretch.models.parser.Snapshot')
    @patch('stretch.models.Release.data_dir', Mock())
    @patch('stretch.models.tarfile')
    @patch('stretch.models.utils')
    def test_get_snapshot(self, utils, tarfile, Snapshot):
        utils.temp_dir.return_value = '/temp_dir'
        tar_file = Mock()
        tarfile.open.return_value = tar_file
        self.release.data_dir = '/data'
        Snapshot.return_value = snapshot = Mock()
        self.assertEquals(self.release.get_snapshot(), snapshot)
        tarfile.open.assert_called_with('/data/snapshot.tar.gz')
        Snapshot.assert_called_with('/temp_dir')
