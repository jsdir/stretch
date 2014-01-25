from unittest import TestCase

from stretch import testutils


class TestMockFileSystem(TestCase):
    def setUp(self):
        self.mock_fs = testutils.MockFileSystem('/root')
        self.mock_fs.set_files({
            'file': 'file_source',
            'empty_folder': {},
            'folder': {
                'f_file': 'f_file_source',
                'f_empty_folder': {},
                'f_folder': {
                    'f_f_file': 'f_f_file_source'
                }
            }
        })
        self.mock_fs.add_file('other_file')
        self.mock_fs.add_file('other_file_content', 'first')
        self.mock_fs.add_file('other_file_content', 'second')
        self.mock_fs.add_file('other_folder/f_file', 'data')

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

        assert self.mock_fs.exists('/root/other_file')
        assert self.mock_fs.exists('/root/other_file_content')
        assert self.mock_fs.exists('/root/other_folder/f_file')

    def test_open(self):
        with self.assertRaises(IOError):
            self.mock_fs.open('/root/undefined')

        self.assertEquals(self.mock_fs.open('/root/folder/f_file').read(),
                          'f_file_source')

    def test_write(self):
        with self.mock_fs.open('/root/folder/f_file', 'w') as f:
            f.write('data')

        self.assertEquals(self.mock_fs.files['/root/folder/f_file'], 'data')

    def test_walk(self):
        self.assertItemsEqual(list(self.mock_fs.walk('/root/undefined')), [])
        self.assertItemsEqual(list(self.mock_fs.walk('/root')), [
            ('/root/other_folder', [], ['f_file']),
            ('/root/empty_folder', [], []),
            ('/root/folder/f_folder', [], ['f_f_file']),
            ('/root/folder/f_empty_folder', [], []),
            ('/root/folder', ['f_folder', 'f_empty_folder'], ['f_file']),
            ('/root', ['other_folder', 'empty_folder', 'folder'],
                      ['other_file', 'file', 'other_file_content']
            )
        ])
        self.assertItemsEqual(list(self.mock_fs.walk('/root/folder')), [
            ('/root/folder', ['f_folder', 'f_empty_folder'], ['f_file']),
            ('/root/folder/f_folder', [], ['f_f_file']),
            ('/root/folder/f_empty_folder', [], [])
        ])
