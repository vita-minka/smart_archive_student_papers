#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m benchmark.run \
  --corpus corpus/chunks.jsonl \
  --questions benchmark/questions.jsonl \
  --split all \
  --output benchmark/results.json
