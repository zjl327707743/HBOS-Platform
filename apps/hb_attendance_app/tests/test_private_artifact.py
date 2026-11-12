import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from hb_attendance_app.hbos_attendance.portal import artifacts


class Denied(Exception):pass


class PrivateArtifactTest(unittest.TestCase):
    def test_only_local_bounded_private_file_is_read_and_remote_or_symlink_targets_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'private';root.mkdir()
            target=root/'source.xlsx';target.write_bytes(b'verified source')
            outside=Path(directory)/'outside.xlsx';outside.write_bytes(b'unrelated')
            link=root/'link.xlsx';link.symlink_to(outside)
            def deny(*args):raise Denied()
            fake=types.SimpleNamespace(get_site_path=lambda *args:str(root),throw=deny,PermissionError=Denied)
            with patch.object(artifacts,'frappe',fake):
                doc=types.SimpleNamespace(is_private=1,file_url='/private/files/source.xlsx',get_full_path=lambda:str(target))
                self.assertEqual(artifacts.private_content(doc),b'verified source')
                for url,path,size in [('https://example.invalid/source.xlsx',target,100),('/files/source.xlsx',target,100),('/private/files/link.xlsx',link,100),('/private/files/source.xlsx',target,2)]:
                    with self.subTest(url=url),self.assertRaises(Denied):
                        artifacts.private_content(types.SimpleNamespace(is_private=1,file_url=url,get_full_path=lambda:str(path)),max_size=size)
