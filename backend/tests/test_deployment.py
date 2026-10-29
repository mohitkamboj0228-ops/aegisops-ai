import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

spec=importlib.util.spec_from_file_location('release_package',Path(__file__).parents[2]/'deploy/package.py')
release_package=importlib.util.module_from_spec(spec);spec.loader.exec_module(release_package)


class PackageTests(unittest.TestCase):
    def test_reproducible_allowlisted_release_without_local_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source'
            for path in ('backend/server.py','backend/ai.py','backend/remediation.py','backend/requirements-ai.txt','deploy/install.sh','frontend/dist/index.html'):
                p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test data')
            (root/'.env').write_text('PRIVATE_SECRET=not-for-upload')
            (root/'data').mkdir();(root/'data/aegis.db').write_text('private database')
            before=release_package.ROOT;release_package.ROOT=root
            try:
                a=Path(tmp)/'a.zip';b=Path(tmp)/'b.zip'
                self.assertEqual(release_package.package(a),release_package.package(b))
                self.assertEqual(a.read_bytes(),b.read_bytes())
                with zipfile.ZipFile(a) as archive:
                    self.assertNotIn('.env',archive.namelist())
                    self.assertFalse(any('aegis.db' in name for name in archive.namelist()))
                    self.assertIn('frontend/dist/index.html',archive.namelist())
                    self.assertEqual(len(archive.read('RELEASE_ID')),64)
            finally:release_package.ROOT=before

    def test_missing_build_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            before=release_package.ROOT;release_package.ROOT=Path(tmp)
            try:
                with self.assertRaisesRegex(ValueError,'Build frontend first'):
                    release_package.package(Path(tmp)/'release.zip')
            finally:release_package.ROOT=before
