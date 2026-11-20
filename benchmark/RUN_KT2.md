# КТ2: запуск живого бенчмарка

Из корня репозитория (Python 3.9+, внешние пакеты не нужны):

```bash
python3 -m benchmark.run --demo
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

`--demo` использует **искусственные** документы и вопросы только для проверки вычислений. Эти цифры **нельзя** выдавать за качество на реальном корпусе.

Реальная оценка:

```bash
python3 -m benchmark.run --corpus corpus/chunks.jsonl --questions benchmark/questions.jsonl --split all --output benchmark/results.json
python3 -m benchmark.run --corpus corpus/chunks.jsonl --questions benchmark/questions.jsonl --split holdout --output benchmark/holdout-results.json
```

`corpus/chunks.jsonl`: одна JSON-строка на фрагмент: `{"chunk_id":"c1","document_id":"d1","text":"текст фрагмента", "year":2024}`. Metadata filters (`year`, `type`, ...) находятся в той же строке.

`benchmark/questions.jsonl`: одна JSON-строка на вопрос: `{"id":"q1","split":"dev","query":"...","gold_document_ids":["d1","d2","d3"],"filters":{}}`.

Для полного бенчмарка требуется **≥20 реальных вопросов** и **≥3 подтверждённых релевантных документа** в каждом; нельзя заменять их искусственными метками. Разметка должна соответствовать документам корпуса. Индекс пересобирается при каждом вызове; измеряемое `latency_ms` охватывает собственно поиск, но не построение индекса и не LLM. Поиск возвращает первые пять **уникальных** документов. Отчёт сохраняет выдачу по каждому вопросу, Recall@5, reciprocal rank, latency и сводные показатели. Тюнинг выполняйте на `dev`, итоговый результат показывайте на `holdout`.

Текущая версия исходного архива **не содержит реальных PDF/размеченного корпуса**; их необходимо добавить отдельно. PDF ingestion и LLM в этом benchmark не реализованы.
