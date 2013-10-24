from unittest import TestCase

from stretch import testutils


class TestMockFileSystem(TestCase):
    def setUp(self):
        self.mock_fs = testutils.MockFileSystem('/root')
        self.mock_fs.set_files({
            'file': 'file_source',
            'empty_folder': None,
            'folder': {
                'f_file': 'f_file_source',
                'f_empty_folder': None,
                'f_folder': {
                    'f_f_file': 'f_f_file_source'
                }
            }
        })

    def test_exists(self):
        assert not self.mock_fs.exists('/root')
        assert not self.mock_fs.exists('/root/undefined')
        assert self.mock_fs.exists('/root/file')
        assert self.mock_fs.exists('/root/empty_folder')
        assert self.mock_fs.exists('/root/folder')

        assert not self.mock_fs.exists('/root/folder/undefined')
        assert self.mock_fs.exists('/root/folder/f_file')
        assert self.mock_fs.exists('/root/folder/f_empty_folder')
        assert self.mock_fs.exists('/root/folder/f_folder')
