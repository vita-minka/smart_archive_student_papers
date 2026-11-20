# Relevance decision worksheet

`relevance_table.csv` has 78 query–document judgments. The `relevance_decision` column contains `YES`/`NO`. These decisions were supplied in a preliminary table and have **not** been independently certified as human-reviewed.

To export and run:

```bash
./RUN_KT2_RELEVANCE.sh
```

Or export separately:

```bash
python3 -m benchmark.review --input benchmark/relevance_table.csv --decision-column relevance_decision --export benchmark/questions_relevance.jsonl
```

For genuinely human-reviewed data, use the original `human_verified` workflow instead.
