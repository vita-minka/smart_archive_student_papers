# Модель данных (проект)

| Сущность | Основные поля | Ограничения |
|---|---|---|
| users | id, role, created_at | роли student/teacher/admin; уточнить политику доступа |
| documents | id, title, author, year, work_type, source_uri, license, owner_id, visibility, sha256, status | проверенные права на хранение/публикацию |
| chunks | id, document_id, page_start, page_end, ordinal, text, token_count | ссылки на существующий документ |
| uploads | id, document_id, state, error, created_at | прозрачный статус обработки |
| queries | id, user_id, query, filters, created_at | приватность и срок хранения |
| answers | id, query_id, content, status, model_version | ответ не содержит неподтверждённых ссылок |
| answer_sources | answer_id, chunk_id, rank, score | источники принадлежат найденным фрагментам |

**Индекс:** postings `term -> [(chunk_id, tf)]`, длины фрагментов, DF и средняя длина. Индекс реализуется собственным кодом; формат хранения уточняется при реализации.

**Права:** visibility и разрешение владельца проверяются до retrieval. Публичный Git содержит лишь спецификацию и вымышленные mock-метаданные.
