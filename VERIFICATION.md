# Verification

Executed in `/Users/hsandaver/Projects/pedestal-zip-metadata` using project `.venv/bin/python`, Python 3.11.16, with Streamlit 1.63.0 installed in that venv. The CLI itself uses only the standard library. The real ZIP integration test invokes Python with `-S`, disabling site-packages.

## Full reproducible check

```sh
sh scripts/test.sh
```

Final execution returned:

```text
files_verified_byte_for_byte: 26
source_unchanged: true
archive_bytes: 70509968
Ran 19 tests in 8.085s
OK
PASS http://127.0.0.1:53251/_stcore/health HTTP 200 ok
Streamlit test server stopped
```

The health-test port is chosen at runtime and will differ on the next run. AppTest emits Streamlit's expected bare-mode `missing ScriptRunContext` warning; there were no UI exceptions or test failures.

The tests cover metadata wording and raw fidelity, Unicode/BOM/fallback decoding, CSV quoting and formula protection, exact JSON/base64 recovery, nested model association, duplicate record retention, same-basename inputs, path traversal, absolute and drive-letter paths, ZIP and local symlinks, duplicate normalized members, malformed ZIP continuation, missing dependencies, malformed dependency syntax, unsupported MTL options, all configured resource bounds, real CLI output read-back, and real ZIP processing through the Streamlit interface.

AppTest asserted five preview tables with row counts `[1, 1, 4, 26, 1]`, seven download controls with nonempty URLs, exact in-session export ZIP payloads, and results retained across reruns. The multiple-ZIP uploader is present with multiple-file mode enabled. AppTest processes the real ZIP by injecting the uploader return value, since it does not drive native browser file selection. Empty selection and invalid ZIP cases also pass. The interface has no folder-path field.

## Real CLI commands executed

```sh
.venv/bin/python scripts/package_sample.py
.venv/bin/python cli.py 'sample_data/Wire nails ABP-HBM-3.405.zip' --output demo_output_zip
.venv/bin/python cli.py '/Users/hsandaver/Downloads/Wire nails ABP-HBM-3.405' --output demo_output_folder
```

Each CLI run returned:

```json
{"catalogue": 1, "variants": 4, "manifest": 26, "issues": 1}
```

Both output folders were read back. The generated demo exports were refreshed on 17 September 2026 to include the Acquia DAM CSV, four supporting CSV reports, and exact JSON, plus their ZIP bundle. Their JSON raw text equals the supplied metadata bytes decoded as UTF-8, and all six members of each generated output ZIP equal the corresponding exported files. The ZIP demo CSV row counts were separately parsed as 1 catalogue, 4 variants, 26 manifest, 1 issue. The tests independently reproduce the real ZIP CLI run into a temporary output directory.

The single actual-data issue is:

```text
code: missing_dependency
member: 3_405_combined_low.obj
detail: 3_405_combined_low.obj.mtl
```

The highV2, mediumV2, and lowV2 variants each have their referenced MTL and six JPG textures. The extra low OBJ remains in the output with missing-dependency status. The license remains `CC by Attribution (Non-Commercial Share-alike)` without an invented version. Download time remains `10/09/2026 08:48:42 GMT+1000 (Australian Eastern Standard Time)`. Digitizer and digitisation date are blank.

The generated sample ZIP contains the real supplied files, verified byte-for-byte before and after packaging, with hashes recorded in `sample_data/provenance.json`. The originals were not modified. No source ZIP was extracted, no data was sent externally, and no server remains running from the health check.

## Development checks

Behavior tests were run and observed failing before the parser, inventory processing, bounded input handling, CLI/export path, and Streamlit UI were implemented. An oversized-material regression was observed failing with `missing` instead of `scan_incomplete`, then fixed and rerun. Additional adversarial regression cases were added against the completed implementation. The full final harness passed.

## Acquia DAM schema verification

The 11 exported column names and their order were compared directly with `Sheet1!A1:K1` in `ABP-3D-CSV-URLs-and-filenames-deduplicated.xlsx`. Both refreshed demo bundles contain byte-identical copies of their individual exports. The source workbook SHA-256 still matches the header snapshot in `sample_data/acquia_schema.json`.

Tests cover every field mapping, actual filenames rather than title-derived names, blank fields, historical dates as text, duplicate row retention, formula protection, CSV quoting, the bundled Acquia DAM CSV, the Acquia DAM preview, and migration of existing UI sessions to the new exports. The app does not validate against a live DAM account.
