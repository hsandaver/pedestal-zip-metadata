"""Integration processes the supplied ZIP through an injected uploader return value."""
from pathlib import Path
import unittest
from unittest.mock import patch
import zipfile
import io
import json

PROJECT = Path(__file__).resolve().parents[1]
SAMPLE = PROJECT / 'sample_data/Wire nails ABP-HBM-3.405.zip'

class UITests(unittest.TestCase):
    def test_real_zip_preview_and_downloads(self):
        self.assertTrue((PROJECT/'app.py').exists(), 'Streamlit UI not implemented')
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(PROJECT/'app.py'), default_timeout=120).run()
        self.assertEqual(len(at.exception), 0)
        self.assertTrue(at.get('file_uploader')[0].proto.multiple_files)
        self.assertEqual(len(at.text_input), 0)
        upload = io.BytesIO(SAMPLE.read_bytes())
        upload.name = SAMPLE.name
        with patch('streamlit.file_uploader', return_value=[upload]):
            at.button(key='process').click().run(timeout=120)
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.dataframe), 5)
        self.assertEqual([len(t.value) for t in at.dataframe], [1, 1, 4, 26, 1])
        downloads = at.get('download_button')
        self.assertEqual(len(downloads), 7)
        self.assertTrue(all(d.proto.url for d in downloads))
        self.assertEqual(downloads[0].proto.label, 'Download Acquia DAM CSV')
        headers = json.loads((PROJECT / 'sample_data/acquia_schema.json').read_text())['columns']
        self.assertEqual(list(at.dataframe[0].value.columns), headers)
        self.assertEqual(at.dataframe[0].value.iloc[0]['DA Filename'], SAMPLE.name)
        result = at.session_state['result']
        self.assertEqual(result['catalogue'][0]['catalogue_id'], 'ABP-HBM-3.405')
        with zipfile.ZipFile(SAMPLE) as source:
            metadata = next(name for name in source.namelist() if name.endswith('.txt'))
            self.assertEqual(result['catalogue'][0]['raw_metadata_text'], source.read(metadata).decode())
        variants = result['variants']
        self.assertEqual(sum(v['dependency_status'] == 'complete' for v in variants), 3)
        self.assertEqual(sorted(len(v['textures']) for v in variants), [0, 6, 6, 6])
        self.assertEqual(result['issues'][0]['detail'], '3_405_combined_low.obj.mtl')
        files = at.session_state['exports']
        with zipfile.ZipFile(io.BytesIO(files['output.zip'])) as z:
            self.assertEqual(z.read('metadata_raw.json'), files['metadata_raw.json'])
        self.assertEqual(json.loads(files['metadata_raw.json'])['catalogue'], result['catalogue'])
        # Download reruns retain results without rereading sources.
        at.run()
        self.assertEqual(len(at.dataframe), 5)
        # A running session upgrades earlier report bundles after an app reload.
        at.session_state['exports'] = {'obsolete_template.csv': b'old export'}
        del at.session_state['processed_names']
        at.run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(set(at.session_state['exports']), {
            'catalogue.csv', 'variants.csv', 'manifest.csv', 'issues.csv',
            'acquia_dam_metadata.csv', 'metadata_raw.json', 'output.zip'})

    def test_empty_upload_reports_error(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(PROJECT / 'app.py')).run()
        at.button(key='process').click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 1)
        self.assertEqual(len(at.get('download_button')), 0)

    def test_invalid_zip_provides_issue_downloads(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(PROJECT / 'app.py')).run()
        upload = io.BytesIO(b'not a ZIP')
        upload.name = 'invalid.zip'
        with patch('streamlit.file_uploader', return_value=[upload]):
            at.button(key='process').click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.warning), 1)
        self.assertEqual(len(at.get('download_button')), 7)
        self.assertEqual(at.session_state['result']['issues'][0]['code'], 'source_error')
