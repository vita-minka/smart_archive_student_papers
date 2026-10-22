# Ветки GitHub

Используем GitHub Flow: `main` и короткие ветки под задачи.

| Ветка | Для чего |
|---|---|
| `main` | Принятая версия |
| `docs/checkpoint-1` | Документация и mock-прототип |
| `feat/bm25-index` | Самостоятельный индекс |
| `feat/pdf-ingestion` | Загрузка и обработка PDF |
| `feat/frontend` | Реальный интерфейс |
| `feat/rag-answer` | Генерация с источниками |
| `test/benchmark` | Gold и метрики |

Команды для начала:
```bash
git checkout -b docs/checkpoint-1
git add .
git commit -m "docs: prepare ThesisHub checkpoint 1"
git push -u origin docs/checkpoint-1
```
После push открыть Pull Request в `main`. Эти команды — инструкция, а не утверждение о выполненной истории.
