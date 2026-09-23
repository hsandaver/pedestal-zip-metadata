"""CSV exports are spreadsheet-safe; JSON preserves the exact decoded values."""
import csv
import io
import json
import zipfile
from pathlib import PurePosixPath

SCHEMAS = {
    'catalogue': ['source_id', 'source_name', 'object_id', 'metadata_path', 'catalogue_id', 'catalogue_id_basis', 'title', 'license', 'author', 'source', 'download_origin', 'download_timestamp', 'attribution_instruction', 'description_html', 'description_text', 'keywords', 'historical_date_text', 'location', 'digitizer', 'digitisation_date', 'metadata_encoding', 'raw_metadata_text'],
    'variants': ['source_id', 'source_name', 'object_id', 'model_path', 'model_format', 'filename_quality_label', 'quality_basis', 'material_files', 'textures', 'missing_dependencies', 'dependency_status'],
    'manifest': ['source_id', 'source_name', 'member', 'size_bytes', 'status'],
    'issues': ['source_id', 'source_name', 'member', 'code', 'detail'],
}

# Sheet1!A1:K1 in ABP-3D-CSV-URLs-and-filenames-deduplicated.xlsx.
# Preserve the supplied field order, with DA Filename renamed to Filename.
ACQUIA_FIELDS = {
    'Filename': 'source_name',
    'DA Primary Title': 'title',
    'DA Number': 'catalogue_id',
    'DA Rights Notes': 'license',
    'DA Responsible Unit': 'author',
    'DA Legacy Location': 'source',
    'attribution_instruction': 'attribution_instruction',
    'DA Asset Description': 'description_text',
    'DA Note': 'keywords',
    'historical_date_text': 'historical_date_text',
    'DA Associated Entities': 'location',
}
EXPORT_NAMES = {key + '.csv' for key in SCHEMAS} | {
    'acquia_dam_metadata.csv', 'metadata_raw.json', 'output.zip',
}


def acquia_rows(result):
    """Map each metadata document to the supplied schema without guessing values."""
    rows = []
    for record in result['catalogue']:
        row = {column: record.get(field, '') for column, field in ACQUIA_FIELDS.items()}
        # Browser uploads are basenames; CLI paths may include parent directories.
        name = row['Filename'] or ''
        row['Filename'] = PurePosixPath(name.replace('\\', '/')).name if name else ''
        rows.append(row)
    return rows


def safe_cell(value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    text = str(value) if value is not None else ''
    # Protect leading whitespace/control-character disguises as well.
    stripped = text.lstrip('\ufeff \t\r\n\v\f')
    if stripped.startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        return "'" + text
    return text


def csv_bytes(rows, columns):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore', quoting=csv.QUOTE_ALL)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: safe_cell(row.get(k, '')) for k in columns})
    return stream.getvalue().encode('utf-8-sig')


def export_files(result):
    files = {'acquia_dam_metadata.csv': csv_bytes(acquia_rows(result), ACQUIA_FIELDS)}
    files.update({key + '.csv': csv_bytes(result[key], SCHEMAS[key]) for key in ('catalogue', 'variants', 'manifest', 'issues')})
    files['metadata_raw.json'] = json.dumps(result, ensure_ascii=False, indent=2).encode('utf-8')
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    files['output.zip'] = stream.getvalue()
    return files
