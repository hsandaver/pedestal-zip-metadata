"""Package supplied data without changing it; verify every archived byte."""
import hashlib
import json
from pathlib import Path
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = Path('/Users/hsandaver/Downloads/Wire nails ABP-HBM-3.405')
TARGET = PROJECT / 'sample_data' / 'Wire nails ABP-HBM-3.405.zip'


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    originals = sorted(p for p in SOURCE.iterdir() if p.is_file())
    assert len(originals) == 26, f'Expected 26 supplied files, found {len(originals)}'
    before = {p.name: {'size_bytes': p.stat().st_size, 'sha256': digest(p)} for p in originals}
    TARGET.parent.mkdir(exist_ok=True)
    if not TARGET.exists():
        with zipfile.ZipFile(TARGET, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for p in originals:
                archive.write(p, p.name)
    with zipfile.ZipFile(TARGET) as archive:
        assert sorted(archive.namelist()) == sorted(before)
        for name, item in before.items():
            with archive.open(name) as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256'], name
    assert before == {p.name: {'size_bytes': p.stat().st_size, 'sha256': digest(p)} for p in originals}, 'Source changed during packaging'
    report = {'provenance': 'Generated ZIP packaging of actual user-supplied local files, not synthetic or externally retrieved data.', 'source_folder': str(SOURCE), 'archive': TARGET.name, 'archive_sha256': digest(TARGET), 'files': before}
    provenance = TARGET.parent/'provenance.json'
    if not provenance.exists():
        provenance.write_text(json.dumps(report, indent=2) + '\n')
    else:
        assert json.loads(provenance.read_text()) == report
    print(json.dumps({'archive': str(TARGET), 'files_verified_byte_for_byte': len(before), 'source_unchanged': True, 'archive_bytes': TARGET.stat().st_size}))

if __name__ == '__main__':
    main()
