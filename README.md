# Pedestal ZIP metadata

A standard-library Python CLI and a local Streamlit UI for downloaded Pedestal3D object ZIPs or object folders. Reads files without extracting ZIP members or changing source files. Combines objects from multiple inputs into CSVs.

## Run the CLI

Python 3.11+ is recommended. The CLI does not need Streamlit or any third-party package.

```sh
cd /Users/hsandaver/Projects/pedestal-zip-metadata
python3.11 cli.py "/path/to/object-one.zip" "/path/to/object-two.zip" --output results
```

For the supplied sample:

```sh
python3.11 cli.py "sample_data/Wire nails ABP-HBM-3.405.zip" --output my_zip_results
python3.11 cli.py "/Users/hsandaver/Downloads/Wire nails ABP-HBM-3.405" --output my_folder_results
```

Use a **new output directory** each time. Existing output paths are refused. Output inside an input folder is refused. Mixed ZIP and folder arguments work. A folder means an already downloaded object tree; ZIP files inside that tree are inventoried, not recursively opened. Quote paths containing spaces. The CLI prints JSON row counts.

Exit code 0 means at least one object was recognized, not that every input is valid. Always review `issues.csv`. Code 2 means no objects were recognized, or an argument error; input failures still produce reports. Code 1 means writing outputs failed. No source content is executed.

## Run the UI

The existing `.venv` has Streamlit installed. For a fresh installation, use a virtual environment, not global pip:

```sh
cd /Users/hsandaver/Projects/pedestal-zip-metadata
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

If using uv instead:

```sh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

Open http://127.0.0.1:8501. Upload one or more object ZIPs and click **Process ZIPs**. No folder path is needed. Click **Download all reports (.zip)** to save the results through your browser. The first preview shows the Acquia DAM columns from the supplied workbook. Click **Download Acquia DAM CSV** for that export. Supporting previews show catalogue rows, model variants, the file manifest, and issues. Download any CSV, exact JSON, or the combined output ZIP. Results survive download reruns. Metadata HTML is displayed as text, never executed.

This is a local tool, not a hosted service. ZIP uploads go to the local Streamlit process. The checked-in configuration binds to `127.0.0.1` and disables usage telemetry. Do not expose this app on a public interface. The app does not send records, models, or textures to Pedestal, Acquia DAM, or another external service.

## Output files

| File | Content |
| --- | --- |
| `acquia_dam_metadata.csv` | The 11 columns from the supplied ABP workbook, with `DA Filename` renamed to `Filename`, in their original order |
| `catalogue.csv` | One row per recognized metadata document, including full `raw_metadata_text` |
| `variants.csv` | One row per accepted 3D model, associated object ID, filename quality label, material references, textures, missing dependencies, scan status |
| `manifest.csv` | Every file member encountered within the member-count bound, including rejected members and duplicate archive names |
| `issues.csv` | Parsing, security, duplicate, encoding, ambiguity, and missing-dependency reports |
| `metadata_raw.json` | All exact decoded values, plus each metadata document's original bytes in `raw_metadata_base64` |
| `output.zip` | The six files above, without source models or textures |

All CSVs have headers even when empty. List-valued dependency columns contain JSON arrays. CSV is UTF-8 with BOM, all cells quoted, CRLF record separators. Embedded Unicode, quotes, commas, and line breaks survive CSV parsing.

### Fidelity and spreadsheet safety

`raw_metadata_text` preserves the entire decoded metadata document, including line endings, unknown text, the attribution instruction, and any UTF-8 BOM character. UTF-8 is attempted first. Invalid UTF-8 falls back to Latin-1 with an `encoding_fallback` issue; this is a reversible byte mapping, not a claim about the file's actual encoding. JSON `raw_metadata_base64` restores the exact bytes for either encoding:

```python
import base64, json
record = json.load(open('results/metadata_raw.json'))['catalogue'][0]
original_bytes = base64.b64decode(record['raw_metadata_base64'])
```

CSV cells beginning with `=`, `+`, `-`, `@`, or leading tab/newline characters receive a leading apostrophe. Leading whitespace or BOM before a formula marker is also protected. This intentionally changes potentially executable spreadsheet cells, including raw text when necessary. Use JSON for unescaped exact values. Spreadsheet software can still infer types or dates, so import historical-date columns as text. Do not remove protection from untrusted input just to make cells look cleaner.

### Field interpretation

- `Title`, `License`, `Author`, and `Source` retain their wording. License versions are not guessed or normalized to a Creative Commons identifier.
- The original download origin and timestamp are separate fields. A download timestamp is not a digitisation timestamp. `digitizer` and `digitisation_date` remain blank; `Author` is not copied to either.
- Description HTML is retained. A plain-text description, Keywords, Date, and Location are also parsed. Historical dates stay text, including approximate and item-specific dates.
- An `ABP-HBM-...` label can be inferred from the title. `catalogue_id_basis` explicitly records that inference. Other identifiers are not guessed.
- Text is recognized as metadata when it has a `Title:` line plus `License:`, `Source:`, or `Description:`. Other `.txt` documents receive an issue and remain in the manifest.
- Multiple metadata documents produce multiple object rows. Models are assigned to a single document in their nearest ancestor directory. If none or several match, the variant is retained with an empty `object_id` and an ambiguity issue. No sibling-folder association is guessed.
- Duplicate source URL, catalogue ID, or exact raw-text identity yields a possible-duplicate issue; both records remain. Each input gets an ordinal plus name-hash source ID. Same-basename inputs stay distinct, including repeated uploads. IDs are batch-order-dependent, not persistent external asset IDs.

### Model dependencies

OBJ `mtllib` declarations are scanned without retaining mesh geometry in memory. Referenced MTL texture maps, including `map_Kd`, are resolved relative to the referencing file. Missing materials or textures remain in variant rows and generate issues. A complete status means declared dependencies were found, not that the geometry or image content is valid. An OBJ without `mtllib` receives an explicit no-material-reference issue.

High, medium, and low are **filename labels only**, not measurements of polygon count or quality. Version labels such as `highV2` are supported. STL, PLY, GLB, GLTF, FBX, DAE, 3DS, USD, USDA, USDC, and USDZ are inventoried as variants. Their embedded or external dependencies are not parsed; status is `not_checked`. MTL map options such as `-s` are flagged as unsupported and yield `scan_incomplete`, never a false complete result.

### Acquia DAM

The `acquia_dam_metadata.csv` export is based on `Sheet1!A1:K1` in the supplied `ABP-3D-CSV-URLs-and-filenames-deduplicated.xlsx`. The `DA Filename` column is exported as `Filename`. Other column names and their order are preserved, including `attribution_instruction` and `historical_date_text`. See [the field mapping](ACQUIA_SCHEMA.md). Each recognized metadata document produces one row. Missing values stay blank; original metadata values are not replaced with the workbook examples. No asset upload or live DAM validation is performed.

## Safety bounds

Defaults per source, defined in `inventory.Limits`:

- 10,000 archive entries or local file entries.
- 1 GiB compressed ZIP input, 2 GiB total declared uncompressed file size.
- 512 MiB per file; 2 MiB per metadata document or material file.
- Maximum compression ratio of 200:1 and dependency line length of 1 MiB.

Count or input-size failures reject the source with a report. Member-level failures remain in the manifest with rejection status. Archives over the total-size bound have all file members rejected. Metadata-specific bounds are reported in issues. No ZIP member is extracted. Absolute, drive-letter, traversal, backslash, symlink, and nonregular file members are rejected. Duplicate normalized ZIP paths are reported and all conflicting entries are excluded from parsing rather than choosing one silently. Local symlink files and directories are not followed. Only read trusted local trees that are not being concurrently modified; this is not a filesystem sandbox against another local process changing ancestor directories during a scan.

Malformed ZIPs do not stop later inputs. Resource limits can reject legitimate very large or unusually compressible data; review issues rather than assuming an empty output is a valid object. Python's ZIP parser still reads the bounded archive's central directory before the member-count check. Batch size is user-controlled, so process large collections in manageable batches.

## Tests and actual sample

```sh
cd /Users/hsandaver/Projects/pedestal-zip-metadata
sh scripts/test.sh
```

The harness verifies the packaged sample byte-for-byte against the original folder, runs unit and real integration tests, starts Streamlit on an ephemeral localhost port, checks `/_stcore/health`, and stops the server. `AppTest` processes the supplied ZIP through an injected uploader return value, asserts table counts and download controls, and inspects the exact export payloads. A real ZIP CLI test runs with Python `-S` to prove it needs no site-packages. Synthetic fixtures used for malformed archives and security tests are labelled as such. The real-sample tests require the supplied folder at the path above; unit tests can run elsewhere with `python3.11 -m unittest discover -s tests -p 'test_core.py'` and the other synthetic test files.

`sample_data/Wire nails ABP-HBM-3.405.zip` is generated packaging of the user's actual supplied 26 files. `sample_data/provenance.json` records the original path, archive SHA-256, and each member's size and SHA-256. It is not synthetic content or externally downloaded evidence. `scripts/package_sample.py` refuses to replace an existing archive, verifies every member against the originals, and checks that the sources are unchanged.

The real folder and real ZIP each produce **1 catalogue row, 4 variant rows, 26 manifest rows, and 1 issue**. Three V2 OBJ variants have their MTL and six JPG textures each. The extra `3_405_combined_low.obj` is retained and reports its missing `3_405_combined_low.obj.mtl`.

Generated, read-back-verified results are in `demo_output_zip/` and `demo_output_folder/`. See `VERIFICATION.md` for the executed checks. The original files were not altered. No git commit was made.
