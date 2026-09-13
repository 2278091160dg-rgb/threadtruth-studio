import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('install_local', Path(__file__).parents[1] / 'install-local.py')
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class LocalInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'recipient'
        self.home.mkdir()
        self.source = self.root / 'release'
        (self.source / '.codex-plugin').mkdir(parents=True)
        (self.source / '.codex-plugin/plugin.json').write_text(json.dumps({
            'name': 'threadtruth-studio', 'version': '1.0.0-beta.2', 'skills': './skills/'}))
        (self.source / 'skills/threadtruth-studio').mkdir(parents=True)
        (self.source / 'skills/threadtruth-studio/SKILL.md').write_text('---\nname: threadtruth-studio\n---\n')

    def test_default_dry_run_never_writes_recipient_state(self):
        result = installer.install(self.source, self.home)
        self.assertFalse((self.home / 'plugins').exists())
        self.assertFalse((self.home / '.agents').exists())
        self.assertEqual(result['selector'], 'threadtruth-studio@personal')

    def test_apply_preserves_other_marketplace_entries_and_name(self):
        market = self.home / '.agents/plugins/marketplace.json'
        market.parent.mkdir(parents=True)
        old = {'name': 'my-personal', 'interface': {'displayName': 'My Tools'},
               'plugins': [{'name': 'unrelated', 'custom': {'keep': True}}]}
        market.write_text(json.dumps(old))
        result = installer.install(self.source, self.home, apply=True)
        data = json.loads(market.read_text())
        self.assertEqual(data['plugins'][0], old['plugins'][0])
        self.assertEqual(data['interface'], old['interface'])
        self.assertEqual(result['selector'], 'threadtruth-studio@my-personal')
        self.assertEqual(data['plugins'][1]['source'], {'source': 'local', 'path': './plugins/threadtruth-studio'})
        self.assertTrue((self.home / 'plugins/threadtruth-studio/skills/threadtruth-studio/SKILL.md').exists())
        self.assertEqual(json.loads(Path(result['marketplace_backup']).read_text()), old)

    def test_existing_source_requires_replace_and_retains_rollback(self):
        installer.install(self.source, self.home, apply=True)
        target = self.home / 'plugins/threadtruth-studio/skills/threadtruth-studio/SKILL.md'
        target.write_text('old payload')
        with self.assertRaises(FileExistsError):
            installer.install(self.source, self.home, apply=True)
        result = installer.install(self.source, self.home, apply=True, replace=True)
        self.assertEqual((Path(result['source_backup']) / 'skills/threadtruth-studio/SKILL.md').read_text(), 'old payload')

    def test_invalid_marketplace_and_symlinks_fail_without_install(self):
        market = self.home / '.agents/plugins/marketplace.json'
        market.parent.mkdir(parents=True)
        market.write_text(json.dumps({'name': 'bad name; command', 'plugins': []}))
        with self.assertRaises(ValueError):
            installer.install(self.source, self.home, apply=True)
        self.assertFalse((self.home / 'plugins').exists())
        market.write_text(json.dumps({'name': 'personal', 'plugins': []}))
        (self.source / 'skills/leak').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            installer.install(self.source, self.home, apply=True)

    def test_different_existing_source_entry_cannot_be_hijacked(self):
        market = self.home / '.agents/plugins/marketplace.json'
        market.parent.mkdir(parents=True)
        market.write_text(json.dumps({'name': 'personal', 'plugins': [
            {'name': 'threadtruth-studio', 'source': {'source': 'git', 'url': 'https://example.org/repo'}}]}))
        with self.assertRaises(ValueError):
            installer.install(self.source, self.home, apply=True, replace=True)

    def test_release_only_allowlist_excludes_private_development_files(self):
        (self.source / '.threadtruth').mkdir()
        (self.source / '.threadtruth/private.txt').write_text('must not copy')
        installer.install(self.source, self.home, apply=True)
        self.assertFalse((self.home / 'plugins/threadtruth-studio/.threadtruth').exists())
