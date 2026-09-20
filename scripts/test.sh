#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-.venv/bin/python}"
"$PYTHON" scripts/package_sample.py
"$PYTHON" -m unittest discover -s tests -v
"$PYTHON" scripts/check_health.py
