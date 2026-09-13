"""Fixed-card behavior using synthetic pixels only; no real visual attestations."""
import copy
from pathlib import Path
import unittest

from PIL import Image, ImageDraw
import test_style_preview as fixtures


def supplied_font():
    candidates = [Path('/System/Library/Fonts/STHeiti Light.ttc'),
                  Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
    font = next((path for path in candidates if path.is_file()), None)
    if font is None:
        raise unittest.SkipTest('A supplied CJK font is required for label rendering')
    return font


class CardTests(fixtures.PreviewTests):
    # Inherit fixture helpers only, not the parent's tests.
    def fixture(self):
        run = self.prepare()
        preview = run['previews'][0]
        path = self.root / 'six-panels.png'
        image = Image.new('RGB', (1600, 1600), 'black')
        cells = [[20, 100, 400, 500], [500, 100, 400, 500], [1000, 100, 400, 500],
                 [20, 800, 100, 100], [500, 800, 400, 600], [1000, 800, 500, 400]]
        colors = [(220, 30, 30), (30, 220, 30), (30, 30, 220),
                  (220, 220, 30), (220, 30, 220), (30, 220, 220)]
        draw = ImageDraw.Draw(image)
        for (x, y, w, h), color in zip(cells, colors):
            draw.rectangle((x, y, x+w-1, y+h-1), fill=color)
        image.save(path)
        self.style = preview['style']
        record = self.m.ingest(self.root, 'test-run', self.style, path, self.generation(preview, 1))
        self.layout = {'original_sha256': record['previews'][0]['original_sha256'], 'cells': cells}
        return record

    def compose_fixture(self):
        self.fixture()
        self.assertTrue(callable(getattr(self.m, 'compose', None)), 'compose workflow is missing')
        return self.m.compose(self.root, 'test-run', self.style, self.layout, supplied_font())

    def test_fixed_cards_center_complete_panels_without_upscale(self):
        record = self.compose_fixture()
        preview = record['previews'][0]
        comp = preview['composition']
        self.assertEqual(comp['transforms'][0]['fitted'], [360, 450])
        self.assertEqual(comp['transforms'][0]['paste'], [44, 155])
        self.assertEqual(comp['transforms'][3]['fitted'], [100, 100])
        self.assertEqual(comp['transforms'][3]['paste'], [174, 826])
        self.assertEqual(comp['transforms'][4]['fitted'], [320, 480])
        self.assertEqual(comp['transforms'][5]['fitted'], [360, 288])
        assets = {a['role']: a for a in self.m.public_assets(record)}
        self.assertEqual(set(assets), {'native-preview', 'display-preview', 'preview-thumbnail'})
        directory = self.m.run_dir(self.root, 'test-run')
        with Image.open(directory / assets['display-preview']['path']) as board:
            self.assertEqual(board.size, (1200, 1200))
            self.assertFalse(board.getexif())
            self.assertLess(sum(255-c for c in board.getpixel((100, 145))), 5)
            pixel = board.getpixel((190, 850))
            self.assertLess(sum(abs(a-b) for a,b in zip(pixel, (220,220,30))), 10)
            self.assertEqual(board.getpixel((100, 850)), (255, 255, 255))
        with Image.open(directory / assets['preview-thumbnail']['path']) as thumb:
            self.assertEqual(thumb.size, (600, 600))
        self.assertNotIn('human_review', preview)
        self.assertEqual(self.m.audit(self.root, 'test-run', style=self.style), [])
        self.assertIn('human review incomplete', ' '.join(self.m.audit(self.root, 'test-run', style=self.style, require_approval=True)))
        self.assertEqual(self.m.compose(self.root, 'test-run', self.style, self.layout, supplied_font()), record)

    def test_compose_rejects_missing_native_and_malformed_observations(self):
        self.fixture()
        self.assertTrue(callable(getattr(self.m, 'compose', None)), 'compose workflow is missing')
        mutations = [lambda d: d.update(original_sha256='0'*64), lambda d: d['cells'].pop(),
                     lambda d: d['cells'][0].__setitem__(0, True),
                     lambda d: d['cells'][0].__setitem__(0, 20.0),
                     lambda d: d['cells'][0].__setitem__(2, 0),
                     lambda d: d['cells'][0].__setitem__(2, 2000),
                     lambda d: d['cells'].__setitem__(1, d['cells'][0]),
                     lambda d: d['cells'].__setitem__(slice(0, 2), d['cells'][1::-1])]
        for mutate in mutations:
            layout = copy.deepcopy(self.layout)
            mutate(layout)
            with self.subTest(layout=layout), self.assertRaises(ValueError):
                self.m.compose(self.root, 'test-run', self.style, layout, supplied_font())
        with self.assertRaises(ValueError):
            self.m.compose(self.root, 'test-run', 'athleisure', self.layout, supplied_font())
        with self.assertRaises((ValueError, OSError)):
            self.m.compose(self.root, 'test-run', self.style, self.layout, self.root/'absent.ttf')

    def test_missing_composition_and_modified_assets_fail_closed(self):
        self.fixture()
        self.assertIn('composition', ' '.join(self.m.audit(self.root, 'test-run', style=self.style)))
        self.assertTrue(callable(getattr(self.m, 'compose', None)), 'compose workflow is missing')
        record = self.m.compose(self.root, 'test-run', self.style, self.layout, supplied_font())
        directory = self.m.run_dir(self.root, 'test-run')
        for asset in self.m.public_assets(record):
            path = directory / asset['path']
            original = path.read_bytes()
            path.write_bytes(b'tampered')
            self.assertTrue(self.m.audit(self.root, 'test-run', style=self.style))
            path.write_bytes(original)
        layout_path = directory / record['previews'][0]['composition']['layout_path']
        layout_path.write_text('{}')
        self.assertTrue(self.m.audit(self.root, 'test-run', style=self.style))

    def test_layout_transform_source_and_approval_binding_tampering_is_rejected(self):
        record = self.compose_fixture()
        directory = self.m.run_dir(self.root, 'test-run')
        path = directory / 'evidence.json'
        mutations = [lambda p: p['composition']['transforms'][0]['paste'].__setitem__(0, 45),
                     lambda p: p['composition']['observed_layout']['cells'][0].__setitem__(0, 21),
                     lambda p: p['composition']['display'].update(path='../outside.jpg'),
                     lambda p: p['composition'].update(original_sha256='0'*64),
                     lambda p: p['composition']['text']['title'].update(text='Truncated'),
                     lambda p: p['composition']['text']['title'].update(bounds=[44, 140, 100, 30])]
        for mutate in mutations:
            changed = copy.deepcopy(record)
            mutate(changed['previews'][0])
            self.m.write_json(path, changed)
            self.assertTrue(self.m.audit(self.root, 'test-run', style=self.style))
        self.m.write_json(path, record)
        review = self.completed_review(record, self.style)
        review['preview_sha256'] = record['previews'][0]['sha256']
        with self.assertRaisesRegex(ValueError, 'human review incomplete'):
            self.m.approve(self.root, 'test-run', self.style, review)
        reviewed = self.m.approve(self.root, 'test-run', self.style, self.completed_review(record, self.style))
        changed = copy.deepcopy(self.layout)
        changed['cells'][0][0] += 1
        with self.assertRaisesRegex(ValueError, 'overwrite registered composition'):
            self.m.compose(self.root, 'test-run', self.style, changed, supplied_font())
        self.assertEqual(self.m.read_json(path), reviewed)

    def test_schema_three_is_read_only_for_compose_and_other_mutations(self):
        record = self.fixture()
        directory = self.m.run_dir(self.root, 'test-run')
        record['schema_version'] = '3.0'
        self.m.write_json(directory/'evidence.json', record)
        before = {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()}
        for mutation in [lambda: self.m.prepare(self.root, 'test-run'),
                         lambda: self.m.compose(self.root, 'test-run', self.style, self.layout, supplied_font()),
                         lambda: self.m.approve(self.root, 'test-run', self.style, {}),
                         lambda: self.m.promote(self.root, 'test-run')]:
            with self.assertRaisesRegex(ValueError, 'historical'):
                mutation()
        self.assertEqual(before, {p.relative_to(directory): p.read_bytes() for p in directory.rglob('*') if p.is_file()})

    def test_long_complete_labels_fit_or_fail_without_truncation(self):
        record = self.fixture()
        cards = self.m._cards()
        native = self.root / 'six-panels.png'
        labels = {'title': 'A complete readable bilingual title / 完整风格标题 '*3,
                  'subtitle': '同款白马甲 · 六姿势预览', 'footer': cards.CONTRACT['footer_text']}
        result = cards.render(native, self.layout['cells'], labels, supplied_font(), self.root, self.style)
        self.assertEqual(result['text']['title']['rendered'].replace('\n', ''), labels['title'])
        x, y, w, h = result['text']['title']['bounds']
        self.assertLessEqual(y+h, 88)
        self.assertLessEqual(x+w, 1156)
        labels['title'] *= 100
        with self.assertRaisesRegex(ValueError, 'cannot fit'):
            cards.render(native, self.layout['cells'], labels, supplied_font(), self.root, self.style)

    def test_gallery_rejects_unregistered_image_paths(self):
        record = self.compose_fixture()
        directory = self.m.run_dir(self.root, 'test-run')
        record['previews'][0]['composition']['display']['path'] = '../outside.jpg'
        self.m.write_json(directory/'evidence.json', record)
        with self.assertRaisesRegex(ValueError, 'path invalid'):
            self.m.gallery(self.root, 'test-run', style=self.style)

    def test_ingest_idempotency_rechecks_retained_original(self):
        record = self.fixture()
        preview = record['previews'][0]
        directory = self.m.run_dir(self.root, 'test-run')
        receipt = self.m.read_json(directory/'native-receipts'/f'{self.style}.json')
        (directory/receipt['retained_path']).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError, 'native output hash mismatch'):
            self.m.ingest(self.root, 'test-run', self.style, self.root/'six-panels.png', preview['generation'])


# Avoid rerunning every inherited integration test in this focused module.
for _name in dir(fixtures.PreviewTests):
    if _name.startswith('test_') and _name not in CardTests.__dict__:
        setattr(CardTests, _name, None)


if __name__ == '__main__':
    unittest.main()
