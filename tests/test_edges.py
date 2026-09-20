"""Additional adversarial and export regression coverage, synthetic data only."""
import io
from pathlib import Path
import tempfile
import unittest
import zipfile
from pedestal import Limits, process
from exports import csv_bytes, safe_cell
from test_safety import zipped

class EdgeTests(unittest.TestCase):
    def test_all_resource_limits(self):
        data = zipped([('a.txt', 'Title: A\nLicense: x'), ('b.obj', 'mtllib b.mtl\n')])
        for limits, expected in [
            (Limits(members=1), 'source_error'),
            (Limits(source_bytes=1), 'source_error'),
            (Limits(member_bytes=1), 'size_limit'),
            (Limits(total_bytes=1), 'size_limit'),
            (Limits(metadata_bytes=1), 'size_limit'),
            (Limits(line_bytes=1), 'member_error'),
        ]:
            with self.subTest(limits=limits):
                r = process([('a.zip', data)], limits)
                self.assertIn(expected, [i['code'] for i in r['issues']])
        bomb = zipped([('big.txt', 'A' * 100000)])
        self.assertIn('compression_limit', [i['code'] for i in process([('bomb.zip', bomb)])['issues']])

    def test_malformed_dependency_keeps_row_and_later_source(self):
        for line in ('mtllib "unterminated', 'mtllib /outside.mtl', 'mtllib ../../outside.mtl'):
            with self.subTest(line=line):
                data = zipped([('a.txt', 'Title: A\nLicense: x'), ('a.obj', line)])
                r = process([('broken.zip', data), ('good.zip', zipped([('b.txt', 'Title: B\nLicense: x')]))])
                self.assertEqual(len(r['catalogue']), 2)
                self.assertEqual(len(r['variants']), 1)
                self.assertIn(r['variants'][0]['dependency_status'], {'missing', 'scan_incomplete'})

    def test_mtl_options_are_not_silently_complete(self):
        data = zipped([('a.txt', 'Title: A\nLicense: x'), ('a.obj', 'mtllib a.mtl'), ('a.mtl', 'map_Kd -s 1 1 1 texture.jpg')])
        r = process([('x.zip', data)])
        self.assertEqual(r['variants'][0]['dependency_status'], 'scan_incomplete')
        self.assertIn('unsupported_mtl_options', [i['code'] for i in r['issues']])

    def test_nearest_ancestor_mapping_and_common_formats(self):
        data = zipped([('root/a.txt', 'Title: A\nLicense: x'), ('root/sub/b.txt', 'Title: B\nLicense: x'), ('root/sub/deep/model.ply', b'fixture'), ('other/model.gltf', b'fixture')])
        r = process([('x.zip', data)])
        row = next(v for v in r['variants'] if v['model_format'] == 'ply')
        self.assertEqual(row['object_id'], next(o['object_id'] for o in r['catalogue'] if o['title'] == 'B'))
        self.assertEqual(row['dependency_status'], 'not_checked')
        self.assertEqual(next(v['object_id'] for v in r['variants'] if v['model_format'] == 'gltf'), '')

    def test_formula_protection_and_csv_roundtrip(self):
        import csv
        for value in ('=1+1', '+cmd', '-1', '@SUM(A1)', '  =1', '\ttext', '\n=1', '\ufeff=1'):
            self.assertEqual(safe_cell(value), "'" + value)
        value = 'Émile, "quoted"\r\nsecond line'
        payload = csv_bytes([{'text': value}], ['text'])
        self.assertTrue(payload.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(list(csv.DictReader(io.StringIO(payload.decode('utf-8-sig'), newline='')))[0]['text'], value)
        self.assertEqual(safe_cell('c1885'), 'c1885')

    def test_duplicate_normalized_members_and_directory_symlink(self):
        data = zipped([('x/a.txt', 'Title: A\nLicense: x'), ('x/./a.txt', 'Title: B\nLicense: x')])
        r = process([('x.zip', data)])
        self.assertEqual(len(r['manifest']), 2)
        self.assertEqual(r['catalogue'], [])
        self.assertEqual(sum(i['code'] == 'duplicate_member' for i in r['issues']), 2)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'root'
            root.mkdir()
            outside = Path(tmp)/'outside'
            outside.mkdir()
            (outside/'a.txt').write_text('Title: Private\nLicense: x')
            (root/'directory').symlink_to(outside, target_is_directory=True)
            r = process([root])
            self.assertEqual(r['catalogue'], [])
            self.assertIn('unsafe_member', [i['code'] for i in r['issues']])
