#!/usr/bin/env python3
"""Standard-library CLI. Sources are read only and output must be new."""
import argparse
import json
from pathlib import Path
from pedestal import process
from exports import export_files


def main():
    parser = argparse.ArgumentParser(description='Read Pedestal ZIPs or local folders into combined metadata CSVs. Never extracts models.')
    parser.add_argument('inputs', nargs='+', type=Path, help='ZIP files or object folders, multiple accepted')
    parser.add_argument('-o', '--output', required=True, type=Path, help='New output directory; existing paths are refused')
    args = parser.parse_args()
    output = args.output.resolve()
    for source in args.inputs:
        if source.is_dir() and (output == source.resolve() or source.resolve() in output.parents):
            parser.error('Output cannot be inside a source folder')
    if args.output.exists():
        parser.error('Output path already exists; choose a new directory')
    result = process(args.inputs)
    files = export_files(result)
    try:
        args.output.mkdir(parents=True, exist_ok=False)
        for name, data in files.items():
            (args.output / name).write_bytes(data)
    except OSError as exc:
        parser.exit(1, f'Output write failed: {exc}\n')
    print(json.dumps({key: len(rows) for key, rows in result.items()}))
    # Reports are written even when all inputs fail.
    return 0 if result['catalogue'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
