"""Synthetic adversarial ZIPs, never external data."""
import io
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path
import pedestal


def zipped(items):
    out = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
            for k, v in items:
                z.writestr(k, v)
    return out.getvalue()


class SafetyTests(unittest.TestCase):
    def test_unsafe_and_duplicate_members_are_reported(self):
        link = zipfile.ZipInfo('link.txt')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        data = zipped([('../escape.txt', 'Title: Bad\nLicense: x'), ('/abs.txt', 'x'), ('C:\\bad.txt', 'x'), (link, '/etc/passwd'), ('same.txt', 'a'), ('same.txt', 'b'), ('ok.txt', 'Title: Good\nLicense: x')])
        r = pedestal.process([('a.zip', data), ('bad.zip', b'not zip'), ('a.zip', zipped([('ok.txt', 'Title: Good\nLicense: x')]))])
        codes = [i['code'] for i in r['issues']]
        self.assertIn('unsafe_member', codes)
        self.assertIn('duplicate_member', codes)
        self.assertIn('source_error', codes)
        self.assertIn('duplicate_record', codes)
        self.assertEqual(len(r['catalogue']), 2)
        self.assertNotEqual(r['catalogue'][0]['source_id'], r['catalogue'][1]['source_id'])
        self.assertEqual(len(r['manifest']), 8)

    def test_bounds_encoding_and_local_symlink(self):
        self.assertTrue(hasattr(pedestal, 'Limits'), 'configurable resource bounds missing')
        data = zipped([('big.txt', 'x' * 2000), ('latin.txt', b'Title: Caf\xe9\nLicense: x'), ('bom.txt', b'\xef\xbb\xbfTitle: Unicode\nLicense: x')])
        r = pedestal.process([('a.zip', data)], limits=pedestal.Limits(metadata_bytes=100, compression_ratio=50))
        self.assertEqual(len(r['catalogue']), 2)
        self.assertIn('encoding_fallback', [i['code'] for i in r['issues']])
        self.assertTrue(any(i['code'] in {'size_limit', 'compression_limit'} for i in r['issues']))
        self.assertTrue(r['catalogue'][1]['raw_metadata_text'].startswith('\ufeff'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'input'
            root.mkdir()
            outside = Path(tmp) / 'outside.txt'
            outside.write_text('Title: Private\nLicense: x')
            (root / 'link.txt').symlink_to(outside)
            r = pedestal.process([root])
            self.assertEqual(r['catalogue'], [])
            self.assertIn('unsafe_member', [i['code'] for i in r['issues']])

    def test_material_text_limit_keeps_flagged_variant(self):
        r = pedestal.process([('x.zip', zipped([('a.txt', 'Title: A\nLicense: x'), ('a.obj', 'mtllib a.mtl\n'), ('a.mtl', 'map_Kd texture.jpg\n' * 10)]))], limits=pedestal.Limits(metadata_bytes=100))
        self.assertEqual(r['variants'][0]['dependency_status'], 'scan_incomplete')
        self.assertIn('member_error', [i['code'] for i in r['issues']])

    def test_ambiguous_documents_and_unrecognized_text(self):
        r = pedestal.process([('x.zip', zipped([('a.txt', 'Title: A\nLicense: x'), ('b.txt', 'Title: B\nLicense: x'), ('readme.txt', 'not metadata'), ('a.obj', 'v 0 0 0')]))])
        self.assertEqual(len(r['catalogue']), 2)
        self.assertEqual(r['variants'][0]['object_id'], '')
        self.assertIn('ambiguous_object', [i['code'] for i in r['issues']])
        self.assertIn('unrecognized_metadata', [i['code'] for i in r['issues']])
