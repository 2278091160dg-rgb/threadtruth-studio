#!/usr/bin/env python3
"""Register a verified release as a personal Codex Plugin. Dry-run by default.

Release-envelope helper, not runtime. Never runs Codex, downloads data, reads
credentials, or hand-edits Codex config. Personal marketplace shape follows
the bundled official plugin-creator; existing metadata/order are preserved.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile
import uuid

NAME = 'threadtruth-studio'
ENTRY_SOURCE = {'source': 'local', 'path': './plugins/threadtruth-studio'}
DIRECTORIES = ('.codex-plugin', 'skills', 'docs')
FILES = ('README.md', 'README.zh-CN.md', 'USER-GUIDE.html', 'LICENSE',
         'CHANGELOG.md', 'CODE_OF_CONDUCT.md', 'CONTRIBUTING.md', 'SECURITY.md',
         'MIGRATION.md', 'PROVENANCE.md', 'RELEASE.md', 'ROADMAP.md', 'install-local.py')


def no_symlinks(path):
    if path.is_symlink():
        raise ValueError('symlinks are not supported')
    if path.is_dir() and any(item.is_symlink() for item in path.rglob('*')):
        raise ValueError('source payload must not contain symlinks')


def install(source, recipient_home, *, apply=False, replace=False):
    source = Path(source)
    no_symlinks(source)
    source = source.resolve()
    home = Path(recipient_home).resolve()
    target = home / 'plugins' / NAME
    marketplace = home / '.agents/plugins/marketplace.json'
    for path in (home / 'plugins', target, home / '.agents', marketplace.parent, marketplace):
        if path.is_symlink():
            raise ValueError('recipient paths must not be symlinks')
    if source == target or target in source.parents:
        raise ValueError('run from a separate extracted release, not the active install')
    manifest = json.loads((source / '.codex-plugin/plugin.json').read_text())
    if manifest.get('name') != NAME or manifest.get('skills') != './skills/':
        raise ValueError('not a ThreadTruth Plugin release')
    version = manifest.get('version', '')
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?(?:\+[A-Za-z0-9.-]+)?', version):
        raise ValueError('invalid release version')
    if not (source / 'skills/threadtruth-studio/SKILL.md').is_file():
        raise ValueError('missing runtime Skill')
    if target.exists() and not replace:
        raise FileExistsError('active source exists; inspect it, then use --replace for a backed-up upgrade')
    if target.exists() and not target.is_dir():
        raise ValueError('active source is not a directory')
    data = json.loads(marketplace.read_text()) if marketplace.exists() else {
        'name': 'personal', 'interface': {'displayName': 'Personal'}, 'plugins': []}
    if not isinstance(data, dict) or not isinstance(data.get('name'), str) or not re.fullmatch(r'[A-Za-z0-9_-]+', data['name']):
        raise ValueError('invalid personal marketplace name')
    if not isinstance(data.get('plugins'), list) or any(not isinstance(row, dict) for row in data['plugins']):
        raise ValueError('invalid marketplace entries')
    if 'interface' in data and not isinstance(data['interface'], dict):
        raise ValueError('invalid marketplace interface')
    existing = [row for row in data['plugins'] if row.get('name') == NAME]
    if len(existing) > 1 or any(row.get('source') != ENTRY_SOURCE for row in existing):
        raise ValueError('conflicting source entry; resolve it explicitly before installing')
    if not existing:
        data['plugins'].append({'name': NAME, 'source': ENTRY_SOURCE,
                                'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                                'category': 'Creative'})
    result = {'applied': False, 'source': str(target), 'marketplace': str(marketplace),
              'selector': f"{NAME}@{data['name']}", 'version': version,
              'source_backup': None, 'marketplace_backup': None}
    if not apply:
        return result
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    target.parent.mkdir(parents=True, exist_ok=True)
    marketplace.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.threadtruth-install-', dir=target.parent))
    backup = target.with_name(f'{NAME}.backup-{stamp}')
    market_backup = marketplace.with_name(f'marketplace.json.backup-{stamp}')
    market_stage = marketplace.with_name(f'.marketplace-{stamp}.tmp')
    replaced = False
    installed = False
    try:
        for name in DIRECTORIES:
            if (source / name).is_dir():
                shutil.copytree(source / name, stage / name,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
        for name in FILES:
            if (source / name).is_file():
                shutil.copy2(source / name, stage / name)
        if target.exists():
            # Default UTC cachebuster follows local iteration convention;
            # pristine archive/source bytes remain unchanged.
            manifest['version'] = version.split('+')[0] + '+codex.' + stamp
            (stage / '.codex-plugin/plugin.json').write_text(json.dumps(manifest, indent=2) + '\n')
        if marketplace.exists():
            shutil.copy2(marketplace, market_backup)
            result['marketplace_backup'] = str(market_backup)
        with market_stage.open('x', encoding='utf-8') as output:
            json.dump(data, output, indent=2)
            output.write('\n')
        if target.exists():
            target.rename(backup)
            replaced = True
            result['source_backup'] = str(backup)
        stage.rename(target)
        installed = True
        market_stage.replace(marketplace)
        result['applied'] = True
        result['installed_version'] = manifest['version']
        return result
    except Exception:
        if installed:
            shutil.rmtree(target)
        if replaced:
            backup.rename(target)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if market_stage.exists():
            market_stage.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--apply', action='store_true', help='copy release and register the personal source')
    parser.add_argument('--replace', action='store_true', help='back up and replace the existing active source')
    args = parser.parse_args()
    try:
        result = install(args.source, Path.home(), apply=args.apply, replace=args.replace)
    except (ValueError, OSError, KeyError) as error:
        parser.exit(1, f'Installation stopped: {error}\n')
    print(json.dumps(result, indent=2))
    print('Source registration only. No Codex config or enabled plugin state was changed.')
    if not args.apply:
        print('Dry run: inspect the paths; repeat with --apply to register.')
    else:
        print(f"Next: codex plugin add {result['selector']} --json")
        print('Then open a NEW Codex task and use $threadtruth-studio with your garment image.')


if __name__ == '__main__':
    main()
