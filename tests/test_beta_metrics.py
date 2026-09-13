import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location('beta_metrics', Path(__file__).parents[1] / 'tools/beta_metrics.py')
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)


class BetaMetricsTests(unittest.TestCase):
    def test_download_categories_are_not_installs_and_ignore_raw_api_fields(self):
        result = metrics.summarize_releases([{
            'tag_name': 'v1.0.0-beta.1', 'body': 'private unrelated content',
            'assets': [
                {'name': 'threadtruth-studio-1.0.0-beta.1.zip', 'download_count': 3},
                {'name': 'threadtruth-studio-white-hooded-puffer-vest-korean-cold-1.0.0-beta.1.zip', 'download_count': 7},
                {'name': 'white-vest-originals.zip.sha256', 'download_count': 9},
            ]}])
        self.assertEqual(result['downloads'], {'plugin': 3, 'media': 7, 'checksum': 9, 'other': 0})
        self.assertNotIn('installs', result)
        self.assertNotIn('private unrelated content', json.dumps(result))

    def test_incomplete_and_negative_api_counts_fail_instead_of_inventing_zero(self):
        for count in (None, -1, True, '3'):
            with self.subTest(count=count), self.assertRaises(ValueError):
                metrics.summarize_releases([{'tag_name': 'v1', 'assets': [{'name': 'x.zip', 'download_count': count}]}])

    def test_overlapping_traffic_windows_are_retained_not_added(self):
        old = {'repository': {'stars': 2, 'forks': 1}, 'traffic': {'views': {'count': 10, 'uniques': 4}}}
        new = {'repository': {'stars': 5, 'forks': 1}, 'traffic': {'views': {'count': 12, 'uniques': 5}}}
        self.assertEqual(metrics.compare(old, new), {'stars_delta': 3, 'forks_delta': 0,
                                                    'traffic_policy': 'overlapping-14-day-snapshots-not-additive'})

    def test_only_successful_opt_in_nonmaintainers_count_once(self):
        base = {'public_id': 'github:tester', 'non_maintainer': True, 'public_consent': True,
                'install': 'pass', 'discovery': 'pass', 'recognition': 'pass',
                'host': 'Codex desktop', 'host_version': '1.2', 'plugin_version': '1.0.0-beta.2',
                'date': '2026-09-14'}
        records = [base, dict(base, public_id='GITHUB:TESTER'), dict(base, public_id='no', public_consent=False),
                   dict(base, public_id='owner', non_maintainer=False), dict(base, public_id='failed', install='fail')]
        result = metrics.installation_summary(records)
        self.assertEqual(result, {'consented_nonmaintainer_installations': 1,
                                  'consented_nonmaintainer_recognitions': 1})

    def test_missing_environment_cannot_be_counted(self):
        self.assertEqual(metrics.installation_summary([{'public_id': 'x', 'non_maintainer': True,
                                                       'public_consent': True, 'install': 'pass'}])[
                             'consented_nonmaintainer_installations'], 0)

    def test_unavailable_network_is_not_zero_and_error_log_is_not_retained(self):
        def fetch(endpoint):
            raise RuntimeError('sensitive external error')
        result = metrics.collect(fetch)
        self.assertEqual(result['repository'], {'status': 'unavailable'})
        self.assertEqual(result['traffic']['views'], {'status': 'unavailable'})
        self.assertNotIn('sensitive', json.dumps(result))

    def test_local_snapshot_refuses_collision_and_symlink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = {'captured_at': '2026-09-13T12:00:00.000000Z'}
            path = metrics.save_snapshot(root, snapshot)
            self.assertEqual(json.loads(path.read_text()), snapshot)
            with self.assertRaises(FileExistsError):
                metrics.save_snapshot(root, snapshot)
            other = root / 'other'
            other.mkdir()
            (other / '.threadtruth').symlink_to(root / '.threadtruth', target_is_directory=True)
            with self.assertRaises(ValueError):
                metrics.save_snapshot(other, snapshot)
