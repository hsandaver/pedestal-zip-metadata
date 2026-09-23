import base64
import csv
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import pedestal
from exports import acquia_rows, export_files
from test_safety import zipped

PROJECT = Path(__file__).resolve().parents[1]

class ExportTests(unittest.TestCase):
    def test_cli_exports_lossless_json_safe_csv(self):
        self.assertTrue((PROJECT / 'cli.py').is_file(), 'CLI not implemented')
        raw = 'Title: =SUM(1,2)\r\nLicense: original unknown version\r\nAuthor: Émile\r\nDescription:\r\n<p>"Quoted", two\nlines</p>\r\n'
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / 'sample.zip'
            src.write_bytes(zipped([('metadata.txt', raw.encode()), ('a.stl', b'test')]))
            out = Path(tmp) / 'out'
            run = subprocess.run([sys.executable, str(PROJECT/'cli.py'), str(src), '--output', str(out)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            summary = json.loads(run.stdout)
            self.assertEqual(summary['catalogue'], 1)
            expected = {'catalogue.csv', 'variants.csv', 'manifest.csv', 'issues.csv', 'acquia_dam_metadata.csv', 'metadata_raw.json', 'output.zip'}
            self.assertEqual({p.name for p in out.iterdir()}, expected)
            with (out/'catalogue.csv').open(encoding='utf-8-sig', newline='') as f:
                row = next(csv.DictReader(f))
            self.assertEqual(row['title'], "'=SUM(1,2)")
            self.assertEqual(row['raw_metadata_text'], raw)
            with (out/'acquia_dam_metadata.csv').open(encoding='utf-8-sig', newline='') as f:
                reader = csv.DictReader(f)
                self.assertEqual(reader.fieldnames, json.loads((PROJECT/'sample_data/acquia_schema.json').read_text())['columns'])
                mapped = next(reader)
            self.assertEqual(mapped['Filename'], 'sample.zip')
            self.assertEqual(mapped['DA Primary Title'], "'=SUM(1,2)")
            self.assertEqual(mapped['DA Rights Notes'], 'original unknown version')
            self.assertEqual(mapped['DA Responsible Unit'], 'Émile')
            self.assertEqual(mapped['DA Asset Description'], '"Quoted", two\nlines')
            self.assertEqual(mapped['historical_date_text'], '')
            exact = json.loads((out/'metadata_raw.json').read_text())['catalogue'][0]
            self.assertEqual(exact['title'], '=SUM(1,2)')
            self.assertEqual(base64.b64decode(exact['raw_metadata_base64']), raw.encode())
            with zipfile.ZipFile(out/'output.zip') as z:
                self.assertEqual(set(z.namelist()), expected - {'output.zip'})
                self.assertEqual(z.read('catalogue.csv'), (out/'catalogue.csv').read_bytes())
            rerun = subprocess.run([sys.executable, str(PROJECT/'cli.py'), str(src), '--output', str(out)], capture_output=True)
            self.assertNotEqual(rerun.returncode, 0, 'Must not overwrite outputs')

    def test_acquia_mapping_uses_object_metadata_and_exact_schema(self):
        raw = ('Title: An object ABP-HBM-1.23\nLicense: Original licence wording\n'
               'Author: Collection unit\nSource: https://example.test/object\n'
               'Please credit the maker.\nDescription:\n'
               '<p>An object.</p><p>Keywords: Wood, Iron</p>'
               '<p>Date: c.1885?</p><p>Location: Original building</p>')
        result = pedestal.process([('actual archive.zip', zipped([('metadata.txt', raw.encode())]))])
        before = json.dumps(result)
        expected = {
            'Filename': 'actual archive.zip',
            'DA Primary Title': 'An object ABP-HBM-1.23',
            'DA Number': 'ABP-HBM-1.23',
            'DA Rights Notes': 'Original licence wording',
            'DA Responsible Unit': 'Collection unit',
            'DA Legacy Location': 'https://example.test/object',
            'attribution_instruction': 'Please credit the maker.',
            'DA Asset Description': 'An object.',
            'DA Note': 'Wood, Iron',
            'historical_date_text': 'c.1885?',
            'DA Associated Entities': 'Original building',
        }
        self.assertEqual(acquia_rows(result), [expected])
        files = export_files(result)
        self.assertEqual(list(csv.DictReader(io.StringIO(files['acquia_dam_metadata.csv'].decode('utf-8-sig')))), [expected])
        self.assertEqual(json.dumps(result), before)
        with zipfile.ZipFile(io.BytesIO(files['output.zip'])) as archive:
            self.assertEqual(archive.read('acquia_dam_metadata.csv'), files['acquia_dam_metadata.csv'])

    def test_acquia_missing_values_filenames_and_duplicate_rows(self):
        result = {'catalogue': [
            {'source_name': '/downloads/my actual name.zip'},
            {'source_name': r'C:\downloads\other.zip'},
            {'source_name': '/downloads/extracted object/'},
            {}, {},
        ]}
        rows = acquia_rows(result)
        self.assertEqual([r['Filename'] for r in rows], ['my actual name.zip', 'other.zip', 'extracted object', '', ''])
        self.assertTrue(all(value == '' for row in rows for key, value in row.items() if key != 'Filename'))
        empty = {key: [] for key in ('catalogue', 'variants', 'manifest', 'issues')}
        reader = csv.DictReader(io.StringIO(export_files(empty)['acquia_dam_metadata.csv'].decode('utf-8-sig')))
        self.assertEqual(reader.fieldnames, list(rows[0]))
        self.assertEqual(list(reader), [])
