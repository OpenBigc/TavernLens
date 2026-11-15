import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from tavernlens.installer import InstallError, install, hdt_running


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.payload = self.root / '解压目录 with spaces' / 'TavernLens'
        self.payload.mkdir(parents=True)
        (self.payload / '_internal').mkdir()
        (self.payload / '_internal' / 'runtime.dll').write_bytes(b'runtime')
        (self.payload / 'TavernLens.Hdt.dll').write_bytes(b'new plugin')
        (self.payload / 'TavernLensBackend.exe').write_bytes(b'new backend')
        self.appdata = self.root / '用户数据'
        self.appdata.mkdir()
        self.target = self.appdata / 'HearthstoneDeckTracker' / 'Plugins' / 'TavernLens'

    def tearDown(self):
        self.temp.cleanup()

    def run_install(self):
        return install(self.payload, self.appdata, is_running=lambda: False)

    def test_new_install_with_spaces_and_chinese_paths(self):
        result = self.run_install()
        self.assertEqual(result, self.target)
        self.assertEqual((result / 'TavernLens.Hdt.dll').read_bytes(), b'new plugin')
        self.assertEqual((result / '_internal' / 'runtime.dll').read_bytes(), b'runtime')
        self.assertEqual(list(self.target.parent.glob('.TavernLens-*')), [])

    def test_update_preserves_configuration_and_other_plugins(self):
        self.run_install()
        (self.target / 'custom.json').write_text('keep me')
        other = self.target.parent / 'AnotherPlugin'
        other.mkdir()
        (other / 'other.dll').write_bytes(b'other plugin')
        local = self.root / 'LocalAppData' / 'TavernLens'
        local.mkdir(parents=True)
        (local / 'settings.json').write_text('personal settings')
        (self.payload / 'TavernLens.Hdt.dll').write_bytes(b'updated plugin')
        self.run_install()
        self.assertEqual((self.target / 'TavernLens.Hdt.dll').read_bytes(), b'updated plugin')
        self.assertEqual((self.target / 'custom.json').read_text(), 'keep me')
        self.assertEqual((other / 'other.dll').read_bytes(), b'other plugin')
        self.assertEqual((local / 'settings.json').read_text(), 'personal settings')

    def test_running_hdt_refuses_without_changing_existing_files(self):
        self.run_install()
        (self.target / 'TavernLens.Hdt.dll').write_bytes(b'original')
        with self.assertRaisesRegex(InstallError, '先退出 HDT'):
            install(self.payload, self.appdata, is_running=lambda: True)
        self.assertEqual((self.target / 'TavernLens.Hdt.dll').read_bytes(), b'original')

    def test_incomplete_archive_does_not_create_installation(self):
        (self.payload / 'TavernLens.Hdt.dll').unlink()
        with self.assertRaisesRegex(InstallError, '不完整'):
            self.run_install()
        self.assertFalse(self.target.exists())

    def test_copy_failure_keeps_original_installation(self):
        self.run_install()
        with patch('tavernlens.installer.shutil.copytree', side_effect=OSError('disk full')):
            with self.assertRaises(InstallError): self.run_install()
        self.assertEqual((self.target / 'TavernLens.Hdt.dll').read_bytes(), b'new plugin')

    def test_commit_failure_restores_original_directory(self):
        self.run_install()
        (self.target / 'TavernLens.Hdt.dll').write_bytes(b'original')
        real_rename = Path.rename
        def fail_stage(path, destination):
            if path.name.startswith('.TavernLens-install-'):
                raise PermissionError('locked')
            return real_rename(path, destination)
        with patch.object(Path, 'rename', fail_stage):
            with self.assertRaises(InstallError): self.run_install()
        self.assertEqual((self.target / 'TavernLens.Hdt.dll').read_bytes(), b'original')
        self.assertEqual(list(self.target.parent.glob('.TavernLens-*')), [])

    def test_missing_appdata_never_installs_relative_to_working_directory(self):
        with self.assertRaisesRegex(InstallError, 'AppData'):
            install(self.payload, '', is_running=lambda: False)
        self.assertFalse(self.target.exists())

    def test_self_install_is_a_noop(self):
        self.run_install()
        self.assertEqual(install(self.target, self.appdata), self.target)

    def test_install_cli_does_not_create_data_service_configuration(self):
        from tavernlens.app import main
        state = self.root / 'unused-service-state'
        with patch('tavernlens.installer.main', return_value=0) as run:
            self.assertEqual(main(['--install', '--quiet', '--state-dir', str(state)]), 0)
        run.assert_called_once_with(quiet=True)
        self.assertFalse(state.exists())

    def test_process_check_works_with_localized_tasklist_output(self):
        result = SimpleNamespace(returncode=0, stdout='"HearthstoneDeckTracker.exe","1234","控制台","1","12,345 K"\n')
        with patch('tavernlens.installer.subprocess.run', return_value=result):
            self.assertTrue(hdt_running())
        result.stdout = '信息: 没有运行的任务匹配指定标准。\n'
        with patch('tavernlens.installer.subprocess.run', return_value=result):
            self.assertFalse(hdt_running())


if __name__ == '__main__': unittest.main()
