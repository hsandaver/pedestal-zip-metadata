# Acquia DAM export mapping

The schema comes from `Sheet1!A1:K1` in the supplied `ABP-3D-CSV-URLs-and-filenames-deduplicated.xlsx`. The app renames `DA Filename` to `Filename` and preserves the other column names and their order in `acquia_dam_metadata.csv`. The workbook's trailing empty columns and separate deduplication log are not part of the schema.

| Export column | Source |
| --- | --- |
| Filename | Actual input ZIP filename, without parent directories |
| DA Primary Title | Title |
| DA Number | Catalogue identifier inferred from the title's ABP-HBM label |
| DA Rights Notes | License, with original wording |
| DA Responsible Unit | Author |
| DA Legacy Location | Source URL |
| attribution_instruction | Attribution instruction |
| DA Asset Description | Plain-text description |
| DA Note | Keywords |
| historical_date_text | Historical date text, without conversion to a calendar date |
| DA Associated Entities | Location text |

The mapping follows the supplied workbook's examples. Values come from each processed input, not from example records in the workbook. In particular, the Source URL remains the one in the object's metadata. The workbook does not act as a URL override list.

Each recognized metadata document produces one row. Multiple model variants do not create extra metadata rows. Multiple metadata documents in one ZIP share that ZIP's filename. Possible duplicates remain in the export and appear in `issues.csv` for review. The workbook's deduplication log does not change this behavior.

For the optional CLI folder input, Filename contains the folder's basename. It does not invent a ZIP filename. Use ZIP inputs when the destination asset is a ZIP.

Missing values stay blank. The app does not invent asset IDs, dates, licences, or other values. CSV formula protection still applies, and exact original values remain in `metadata_raw.json`. Supporting reports retain the internal identifiers and provenance fields that are not part of this schema.

The browser provides a direct **Download Acquia DAM CSV** button and an Acquia DAM preview. **Download all reports (.zip)** includes the same CSV alongside the supporting reports. The CLI also writes the Acquia DAM CSV into its output directory.

This mapping follows the supplied workbook, with the filename column renamed to `Filename`. The app does not upload assets or validate fields against a live Acquia DAM account.

The export headers and source workbook SHA-256 are recorded in `sample_data/acquia_schema.json`. The app does not require the workbook or a spreadsheet library at runtime.
