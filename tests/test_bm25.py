import unittest
from search.bm25 import BM25Index, tokenize
from benchmark.run import run_benchmark

class TestBM25(unittest.TestCase):
    def test_unicode(self):
        self.assertEqual(tokenize('Ёжик, ТЕСТ!'), ['ёжик', 'тест'])

    def test_empty(self):
        self.assertEqual(BM25Index([]).search('query'), [])
        self.assertEqual(BM25Index([{'chunk_id':'1','document_id':'d','text':'test'}]).search(''), [])

    def test_deduplicate_documents(self):
        chunks=[{'chunk_id':'1','document_id':'a','text':'hello hello'},
                {'chunk_id':'2','document_id':'a','text':'hello'},
                {'chunk_id':'3','document_id':'b','text':'hello'}]
        ids=[r['document_id'] for r in BM25Index(chunks).search('hello')]
        self.assertEqual(len(ids), len(set(ids)))

    def test_filters(self):
        chunks=[{'chunk_id':'1','document_id':'a','text':'hello','year':2020},
                {'chunk_id':'2','document_id':'b','text':'hello','year':2024}]
        self.assertEqual(BM25Index(chunks).search('hello',filters={'year':2024})[0]['document_id'], 'b')

    def test_metrics(self):
        chunks=[{'chunk_id':str(i),'document_id':str(i),'text':'hello'} for i in range(3)]
        questions=[{'id':'q1','query':'hello','gold_document_ids':['0','1','2']}]
        report=run_benchmark(chunks, questions, strict=False)
        self.assertEqual(report['summary']['recall_at_5'],1)
        self.assertEqual(report['summary']['mrr'],1)

if __name__ == '__main__':
    unittest.main()
