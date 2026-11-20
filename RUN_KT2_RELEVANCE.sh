#!/bin/sh
set -eu
cd "$(dirname "$0")"
echo "Relevance decisions from supplied table; not certified as human-verified."
python3 -m benchmark.review \
  --input benchmark/relevance_table.csv \
  --decision-column relevance_decision \
  --export benchmark/questions_relevance.jsonl
python3 -m benchmark.run \
  --corpus corpus/chunks.jsonl \
  --questions benchmark/questions_relevance.jsonl \
  --split all \
  --output benchmark/results_relevance.json
