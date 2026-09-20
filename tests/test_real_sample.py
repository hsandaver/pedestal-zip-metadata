"""Real ZIP CLI integration: read its output files back, not just exit status."""
import base64
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
SAMPLE = PROJECT / 'sample_data' / 'Wire nails ABP-HBM-3.405.zip'

class RealSampleTests(unittest.TestCase):
    def test_real_zip_cli_counts_and_byte_fidelity(self):
        self.assertTrue(SAMPLE.exists(), 'Run scripts/package_sample.py first')
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'results'
            run = subprocess.run([sys.executable, '-S', str(PROJECT/'cli.py'), str(SAMPLE), '-o', str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout), dict(catalogue=1, variants=4, manifest=26, issues=1))
            result = json.loads((output/'metadata_raw.json').read_text())
            with zipfile.ZipFile(SAMPLE) as archive:
                metadata_name = next(n for n in archive.namelist() if n.endswith('.txt'))
                raw_bytes = archive.read(metadata_name)
                self.assertEqual(len(archive.namelist()), len(result['manifest']))
            row = result['catalogue'][0]
            self.assertEqual(base64.b64decode(row['raw_metadata_base64']), raw_bytes)
            self.assertEqual(row['raw_metadata_text'], raw_bytes.decode('utf-8'))
            self.assertEqual(row['license'], 'CC by Attribution (Non-Commercial Share-alike)')
            self.assertEqual(row['download_timestamp'], '10/09/2026 08:48:42 GMT+1000 (Australian Eastern Standard Time)')
            self.assertEqual(row['digitizer'], '')
            self.assertIn('c1885', row['historical_date_text'])
            self.assertEqual(row['attribution_instruction'], 'Please attribute appropriately.')
            for key in ('catalogue', 'variants', 'manifest', 'issues'):
                with (output/(key+'.csv')).open(encoding='utf-8-sig', newline='') as stream:
                    self.assertEqual(len(list(csv.DictReader(stream))), len(result[key]))
            complete = [v for v in result['variants'] if v['dependency_status'] == 'complete']
            self.assertEqual(len(complete), 3)
            self.assertEqual({v['filename_quality_label'] for v in complete}, {'high', 'medium', 'low'})
            self.assertTrue(all(len(v['textures']) == 6 for v in complete))
            issue = result['issues'][0]
            self.assertEqual(issue['code'], 'missing_dependency')
            self.assertEqual(issue['member'], '3_405_combined_low.obj')
            self.assertEqual(issue['detail'], '3_405_combined_low.obj.mtl')
