from unittest import TestCase
from nose.tools import eq_, assert_raises

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

    def test_open(self):
        with assert_raises(IOError):
            self.mock_fs.open('/root/undefined')

        eq_(self.mock_fs.open('/root/folder/f_file').read(), 'f_file_source')

    def test_walk(self):
        self.assertItemsEqual(list(self.mock_fs.walk('/root/undefined')), [])
        self.assertItemsEqual(list(self.mock_fs.walk('/root')), [
            ('/root', ['empty_folder', 'folder'], ['file']),
            ('/root/folder', ['f_folder', 'f_empty_folder'], ['f_file']),
            ('/root/folder/f_folder', [], ['f_f_file']),
            ('/root/folder/f_empty_folder', [], []),
            ('/root/empty_folder', [], [])
        ])
        self.assertItemsEqual(list(self.mock_fs.walk('/root/folder')), [
            ('/root/folder', ['f_folder', 'f_empty_folder'], ['f_file']),
            ('/root/folder/f_folder', [], ['f_f_file']),
            ('/root/folder/f_empty_folder', [], [])
        ])


def test_mock_attr():
    eq_(testutils.mock_attr(key='value').key, 'value')


def test_check_items_equal():
    assert testutils.check_items_equal([1, 2], [2, 1])
    assert not testutils.check_items_equal([1, 2], [1, 2, 3])
