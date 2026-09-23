# Using Pedestal ZIP metadata

## What it does

This local tool reads downloaded Pedestal3D object ZIPs or folders and combines their metadata into CSV files. Use it to prepare catalogue records, list model files, and find missing OBJ materials or textures before further processing.

For each recognized metadata text file, it records the title, author, licence, source, description, and other available fields. It keeps the original metadata text as well. It lists model variants and inventories the files in each input.

For OBJ models, it follows material references to MTL files and texture references to image files. Other model formats appear in the inventory, but their dependencies are not checked. Labels such as high, medium, and low come from filenames. The tool does not measure model quality or validate geometry.

The tool reads source files without modifying them or extracting ZIP members. It does not download objects from Pedestal3D, convert models, or upload files to Acquia DAM. Its output ZIP contains reports only, not models or textures.

## Prepare the inputs

1. Download the object ZIPs from Pedestal3D, or locate folders you have already downloaded.
2. Keep each object's metadata text, models, materials, and textures together in their original folder structure.
3. Choose either the browser interface or the command line below. Both produce the same report formats.

A metadata text file must contain a `Title:` line and at least one `License:`, `Source:`, or `Description:` line. Unrecognized text files still appear in the file inventory and produce an issue.

You can process several objects together. ZIP files inside an input folder are listed as files but are not opened recursively. Select those ZIPs separately if you want to process their contents.

## Procedure using the browser interface

### 1. Start the application

Open Terminal and run:

```sh
cd /Users/hsandaver/Projects/pedestal-zip-metadata
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1
```

This project already has a Python virtual environment. If setting up a fresh copy, install Python 3.11 or later and run these commands once before starting the application:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Keep the Terminal window open while using the application.

### 2. Open the application

Open [the local application](http://127.0.0.1:8501) in your browser. If Terminal reports a different port, use the local address it prints.

### 3. Select the inputs

Use **Upload object ZIPs** to choose one or more ZIPs. No input or output folder path is needed in the browser. If you only have an extracted object folder, compress it into a ZIP first or use the optional command-line procedure below.

For a trial run, choose this supplied ZIP:

```text
/Users/hsandaver/Projects/pedestal-zip-metadata/sample_data/Wire nails ABP-HBM-3.405.zip
```

### 4. Process and review

Click **Process ZIPs**. Check the reported row counts, then review the tables using the review procedure below. A completed run can still contain errors or missing dependencies.

For the supplied sample, expect 1 object row, 4 model variants, 26 files, and 1 issue. The issue reports that `3_405_combined_low.obj` refers to a missing material file, `3_405_combined_low.obj.mtl`.

### 5. Save the results

Click **Download Acquia DAM CSV** for the metadata export in your supplied schema. Click **Download all reports (.zip)** to save it with the five supporting reports. You can also download individual files. Choose a location that identifies the input batch and processing date.

Download the current results before processing another batch. Clicking **Process ZIPs** replaces the displayed results.

### 6. Stop the application

Return to Terminal and press `Control+C`.

## Procedure using the command line

The command-line tool uses Python's standard library. It does not require Streamlit or the dependency installation above.

1. Open Terminal and enter the project directory.

   ```sh
   cd /Users/hsandaver/Projects/pedestal-zip-metadata
   ```

2. Run the tool with one or more input paths and a new output directory. This example uses the supplied sample.

   ```sh
   python3.11 cli.py "sample_data/Wire nails ABP-HBM-3.405.zip" --output results_trial_01
   ```

   For your own batch, replace the example paths below with actual ZIP or folder paths.

   ```sh
   python3.11 cli.py "/path/to/object-one.zip" "/path/to/object-two-folder" --output results_batch_01
   ```

   Quote paths that contain spaces. The output directory must not already exist and must not be inside an input folder. Choose a new directory name for each run.

3. Read the row counts printed in Terminal. Open the output directory and review the reports below.
4. Resolve or document issues, then rerun into a new directory if needed. Keep the reports with a record of which inputs you processed.

Exit code `0` means the tool recognized at least one metadata document. It does not mean every input passed. Code `2` means no metadata documents were recognized or the command arguments were invalid. Processing failures still produce reports when output writing succeeds; argument errors do not. Code `1` means output writing failed, so any files written may be incomplete.

## Review the results

| Report | What to check |
| --- | --- |
| `issues.csv` | Read this first. Check missing dependencies, unreadable inputs, rejected files, duplicate records, and ambiguous model associations. |
| `acquia_dam_metadata.csv` | Confirm the 11 supplied columns and the actual ZIP filename. Review the mapped metadata before importing. |
| `catalogue.csv` | Confirm the expected objects appear and check titles, identifiers, descriptions, licences, and attribution instructions against the source metadata. Each recognized metadata document creates one row. |
| `variants.csv` | Check model paths, object associations, material files, textures, and dependency status. An empty `object_id` means the tool could not assign the model to exactly one metadata document. |
| `manifest.csv` | Check which files the tool encountered and whether it accepted or rejected them. An accepted file has passed inventory checks, not a content-validity test. |
| `metadata_raw.json` | Keep this for exact decoded metadata and original metadata bytes stored as base64. |

Interpret `dependency_status` as follows:

- `complete` means the scan found the declared dependencies. It does not prove the model or images are valid. An OBJ without a material declaration can have this status and a `no_material_reference` issue.
- `missing` means at least one referenced dependency was not found among accepted files.
- `scan_incomplete` means the tool could not finish interpreting the references. Read the related issues.
- `not_checked` means the tool did not scan that model format's dependencies.

For missing dependencies, use the reported path to check the original download. Obtain a complete download or correct the input package as appropriate, then rerun. For ambiguous associations, check that each object's model files sit under the appropriate metadata folder. Duplicate warnings retain both records, so review them before combining records elsewhere.

Import historical dates and catalogue identifiers as text in spreadsheet software. CSV cells that could act as formulas receive a protective leading apostrophe. Use `metadata_raw.json` when you need exact values without that CSV protection.

The download timestamp is not a digitisation date. The tool leaves `digitizer` and `digitisation_date` blank. Generated object IDs identify records within a batch and should not be used as permanent collection identifiers.

## Preparing records for Acquia DAM

The Acquia DAM CSV follows the 11-column schema in your supplied ABP workbook, with `DA Filename` renamed to `Filename`. [The field mapping](ACQUIA_SCHEMA.md) lists each source field. The export uses each uploaded ZIP's actual filename and metadata values. Missing metadata stays blank, and duplicate records remain available for review. Asset uploads and imports happen separately; the app does not connect to Acquia DAM.

## Troubleshooting

- If no objects appear, read `issues.csv` and check that the input contains recognizable metadata text. Model files alone do not create catalogue rows.
- If the CLI refuses an output path, choose a new directory outside every input folder.
- If files are rejected for size or compression limits, check the issues before treating the results as complete. Default limits include 10,000 entries per input, a 1 GiB compressed ZIP, 2 GiB total declared file size, 512 MiB per file, and 2 MiB per metadata or material file.

Keep the application bound to localhost. Process large collections in manageable batches, and avoid changing input folders while a scan runs.
