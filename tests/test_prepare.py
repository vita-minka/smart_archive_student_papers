import csv
import json
import tempfile
import unittest
from pathlib import Path

from benchmark.prepare import build_corpus, export_gold, write_worksheet
from benchmark.run import run_benchmark


class TestPrepare(unittest.TestCase):
    def test_import_worksheet_export_and_live_benchmark(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'documents'
            source.mkdir()
            # Six simple documents are enough for 3 relevant IDs per question.
            for i in range(6):
                (source / f'research{i}.txt').write_text(
                    'Студенческая исследовательская работа: поиск документов и обработка текста. ' * 15,
                    encoding='utf-8')
            manifest, chunks, warnings = build_corpus(source, root / 'corpus')
            self.assertEqual(len(manifest), 6)
            self.assertTrue(chunks)
            self.assertFalse(warnings)
            worksheet = root / 'questions.csv'
            write_worksheet(worksheet)
            self.assertRaises(ValueError, write_worksheet, worksheet)
            with worksheet.open(encoding='utf-8-sig', newline='') as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                row['query'] = 'поиск документов обработка текста'
                row['gold_document_ids'] = ';'.join(x['document_id'] for x in manifest[:3])
            with worksheet.open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            questions_jsonl = root / 'questions.jsonl'
            self.assertEqual(export_gold(worksheet, root / 'corpus/manifest.json', questions_jsonl), 20)
            questions = [json.loads(line) for line in questions_jsonl.read_text(encoding='utf-8').splitlines()]
            result = run_benchmark(chunks, questions)
            self.assertEqual(result['summary']['questions'], 20)
            self.assertEqual(len([q for q in questions if q['split'] == 'holdout']), 10)

    def test_unknown_gold_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = root / 'manifest.json'
            manifest.write_text(json.dumps([{'document_id': 'd1', 'chunks': 1}]), encoding='utf-8')
            worksheet = root / 'q.csv'
            write_worksheet(worksheet)
            rows = list(csv.DictReader(worksheet.open(encoding='utf-8-sig', newline='')))
            for row in rows:
                row.update(query='пример запроса', gold_document_ids='d1;d2;d3')
            with worksheet.open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            with self.assertRaisesRegex(ValueError, 'unknown or empty documents'):
                export_gold(worksheet, manifest, root / 'out.jsonl')
