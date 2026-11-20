#!/bin/sh
set -eu
cd "$(dirname "$0")"
echo "WARNING: Assistant-prechecked labels, NOT HUMAN VERIFIED; preliminary metrics only."
python3 -m benchmark.review --input benchmark/assistant_prechecked.csv --assistant-prechecked --export benchmark/questions_prechecked.jsonl
python3 -m benchmark.run --corpus corpus/chunks.jsonl --questions benchmark/questions_prechecked.jsonl --split all --output benchmark/results_prechecked.json
