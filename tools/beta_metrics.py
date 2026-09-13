"""Opt-in Beta summaries. Development-only; never publishes or adds telemetry."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess

REPOSITORY = '2278091160dg-rgb/threadtruth-studio'
TRAFFIC_POLICY = 'overlapping-14-day-snapshots-not-additive'


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError('missing or invalid count')
    return value


def summarize_releases(releases):
    totals = dict.fromkeys(('plugin', 'media', 'checksum', 'other'), 0)
    assets = []
    for release in releases:
        for asset in release['assets']:
            name = asset['name']
            if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,200}', name):
                raise ValueError('invalid asset name')
            category = 'other'
            if name.endswith('.sha256'):
                category = 'checksum'
            elif re.fullmatch(r'threadtruth-studio-\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?\.zip', name):
                category = 'plugin'
            elif re.fullmatch(r'threadtruth-studio-[a-z][a-z0-9-]+-\d+\.\d+\.\d+(?:-[A-Za-z0-9.]+)?\.zip', name):
                category = 'media'
            downloads = count(asset.get('download_count'))
            totals[category] += downloads
            assets.append({'release': release['tag_name'], 'name': name,
                           'category': category, 'downloads': downloads})
    return {'downloads': totals, 'assets': assets}


def installation_summary(records):
    installed, recognized = set(), set()
    for row in records:
        if row.get('public_consent') is not True or row.get('non_maintainer') is not True:
            continue
        required = ('public_id', 'host', 'host_version', 'plugin_version', 'date')
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in required):
            continue
        if row.get('install') != 'pass':
            continue
        identity = row['public_id'].strip().casefold()
        installed.add(identity)
        if row.get('discovery') == 'pass' and row.get('recognition') == 'pass':
            recognized.add(identity)
    # Never copy tester identities or free text into a metrics snapshot.
    return {'consented_nonmaintainer_installations': len(installed),
            'consented_nonmaintainer_recognitions': len(recognized)}


def compare(previous, current):
    result = {'traffic_policy': TRAFFIC_POLICY}
    for key in ('stars', 'forks'):
        before, after = previous.get('repository', {}).get(key), current.get('repository', {}).get(key)
        result[f'{key}_delta'] = after - before if type(before) is int and type(after) is int else None
    return result


def gh_read(endpoint):
    result = subprocess.run(['gh', 'api', '--method', 'GET', '--paginate', '--slurp', endpoint],
                            capture_output=True, text=True, timeout=60, check=True)
    pages = json.loads(result.stdout)
    if len(pages) == 1:
        return pages[0]
    if all(isinstance(page, list) for page in pages):
        return [item for page in pages for item in page]
    raise ValueError('unexpected pagination')


def collect(fetch=gh_read):
    def safe(endpoint, transform):
        try:
            return transform(fetch(f'repos/{REPOSITORY}{endpoint}'))
        except (ValueError, KeyError, TypeError, RuntimeError, OSError, subprocess.SubprocessError):
            # No raw API bodies, error strings, credentials or fallback zeros.
            return {'status': 'unavailable'}

    def traffic(data, series):
        return {'count': count(data['count']), 'uniques': count(data['uniques']),
                'days': [{'timestamp': day['timestamp'], 'count': count(day['count']),
                          'uniques': count(day['uniques'])} for day in data[series]]}

    def ranks(data, field):
        return [{field: row[field], 'count': count(row['count']), 'uniques': count(row['uniques'])}
                for row in data]

    return {'schema_version': '1.0', 'repository_name': REPOSITORY,
            'captured_at': datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
            'traffic_policy': TRAFFIC_POLICY,
            'repository': safe('', lambda d: {'stars': count(d['stargazers_count']),
                                              'forks': count(d['forks_count'])}),
            'releases': safe('/releases?per_page=100', summarize_releases),
            'traffic': {
                'views': safe('/traffic/views', lambda d: traffic(d, 'views')),
                'clones': safe('/traffic/clones', lambda d: traffic(d, 'clones')),
                'referrers': safe('/traffic/popular/referrers', lambda d: ranks(d, 'referrer')),
                'paths': safe('/traffic/popular/paths', lambda d: ranks(d, 'path'))},
            'installations': {'status': 'unavailable', 'reason': 'no-consented-register-provided'}}


def save_snapshot(root, snapshot):
    root = Path(root).resolve()
    directory = root / '.threadtruth' / 'beta-metrics'
    for path in (root / '.threadtruth', directory):
        if path.is_symlink():
            raise ValueError('local evidence must not follow symlinks')
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = snapshot['captured_at']
    if not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{6}Z', timestamp):
        raise ValueError('invalid snapshot timestamp')
    path = directory / (timestamp.replace(':', '-') + '.json')
    with path.open('x', encoding='utf-8') as output:
        json.dump(snapshot, output, ensure_ascii=False, indent=2)
        output.write('\n')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--install-register', type=Path,
                        help='optional local JSON list of sanitized, consented feedback records')
    args = parser.parse_args()
    snapshot = collect()
    if args.install_register:
        snapshot['installations'] = installation_summary(json.loads(args.install_register.read_text()))
    path = save_snapshot(args.root, snapshot)
    print(f'Local snapshot saved: {path.relative_to(args.root.resolve())}')
    print('No public files changed. Review summaries before copying to the public register.')
    unavailable = snapshot['repository'].get('status') == 'unavailable'
    return 1 if unavailable else 0
