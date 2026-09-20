"""Synthetic unit fixtures; real sample integration is separate."""
import unittest
import importlib.util

class MetadataTests(unittest.TestCase):
    def test_metadata_fidelity(self):
        self.assertIsNotNone(importlib.util.find_spec('pedestal'), 'metadata parser is not implemented')
        from pedestal import parse_metadata
        raw = 'Model downloaded from Pedestal 3D instance: https://example.org/ at 10/09/2026 08:48 GMT+1000\r\nTitle: Nails ABP-HBM-3.405\r\nLicense: CC wording\r\nAuthor: Faculty\r\nSource: https://example.org/r/a\r\nPlease attribute appropriately.\r\nDescription:\r\n<p>A &amp; B<br>Keywords: Nails<br>Date: c1885<br>Location: Room</p>\r\n'
        row = parse_metadata(raw)
        self.assertEqual(row['raw_metadata_text'], raw)
        self.assertEqual(row['historical_date_text'], 'c1885')
        self.assertEqual(row['catalogue_id'], 'ABP-HBM-3.405')
        self.assertEqual(row['license'], 'CC wording')
        self.assertEqual(row['digitizer'], '')
        self.assertEqual(row['download_timestamp'], '10/09/2026 08:48 GMT+1000')
        self.assertEqual(row['attribution_instruction'], 'Please attribute appropriately.')
        self.assertEqual(row['description_text'], 'A & B')

class InventoryTests(unittest.TestCase):
    def test_nested_models_dependencies_and_ambiguity(self):
        import pedestal, tempfile, zipfile
        from pathlib import Path
        self.assertTrue(hasattr(pedestal, 'process'), 'inventory processing missing')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'sample.zip'
            with zipfile.ZipFile(path, 'w') as z:
                z.writestr('nested/meta.txt', 'Title: Object\nLicense: Original\nDescription:\nText')
                z.writestr('nested/shape_highV2.obj', 'mtllib ./shape.mtl\nv 0 0 0\n')
                z.writestr('nested/shape.mtl', 'map_Kd texture.jpg\n')
                z.writestr('nested/texture.jpg', b'fixture')
                z.writestr('nested/broken_low.obj', 'mtllib missing.mtl\n')
                z.writestr('nested/model.glb', b'fixture')
            result = pedestal.process([path])
            self.assertEqual(len(result['catalogue']), 1)
            self.assertEqual(len(result['manifest']), 6)
            self.assertEqual(len(result['variants']), 3)
            high = next(v for v in result['variants'] if v['filename_quality_label'] == 'high')
            self.assertEqual(high['dependency_status'], 'complete')
            self.assertEqual(high['textures'], ['nested/texture.jpg'])
            self.assertIn('missing_dependency', [i['code'] for i in result['issues']])
            self.assertEqual(result['variants'][0]['object_id'], result['catalogue'][0]['object_id'])

if __name__ == '__main__':
    unittest.main()
