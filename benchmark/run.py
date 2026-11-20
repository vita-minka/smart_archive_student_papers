"""Run: python3 -m benchmark.run --demo (from repository root)."""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

from search.bm25 import BM25Index


def read_jsonl(path):
    with open(path, encoding='utf-8') as source:
        for line_no, line in enumerate(source, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f'{path}:{line_no}: invalid JSON: {exc}') from exc


def run_benchmark(chunks, questions, k1=1.5, b=0.75, top_k=5, strict=True):
    if strict and len(questions) < 20:
        raise ValueError('For the real KT2 benchmark, at least 20 questions are required')
    index = BM25Index(chunks, k1=k1, b=b)
    available = {str(chunk['document_id']) for chunk in chunks}
    results = []
    for question in questions:
        gold = set(map(str, question['gold_document_ids']))
        if len(gold) < 3:
            raise ValueError(f"Question {question['id']} has fewer than 3 gold documents")
        if not gold <= available:
            raise ValueError(f"Question {question['id']} has unknown gold document IDs: {sorted(gold-available)}")
        start = time.perf_counter()
        ranked = index.search(question['query'], top_k=top_k, filters=question.get('filters'))
        elapsed_ms = (time.perf_counter() - start) * 1000
        ids = [hit['document_id'] for hit in ranked]
        hits = len(gold.intersection(ids))
        first = next((rank for rank, id_ in enumerate(ids, 1) if id_ in gold), None)
        results.append({'id': question['id'], 'query': question['query'], 'split': question.get('split', 'unspecified'),
                        'gold_document_ids': sorted(gold), 'ranked': ranked, 'recall_at_5': hits/len(gold),
                        'reciprocal_rank': 1/first if first else 0.0, 'latency_ms': elapsed_ms})
    summary = {'questions': len(results), 'chunks': index.N, 'documents': len(available),
               'recall_at_5': statistics.mean(r['recall_at_5'] for r in results),
               'mrr': statistics.mean(r['reciprocal_rank'] for r in results),
               'latency_mean_ms': statistics.mean(r['latency_ms'] for r in results),
               'latency_p95_ms': sorted(r['latency_ms'] for r in results)[min(len(results)-1, int(0.95 * len(results)))],
               'k1': k1, 'b': b, 'top_k': top_k}
    return {'summary': summary, 'results': results}


def main():
    parser = argparse.ArgumentParser(description='Live BM25 benchmark; use --demo for explicitly synthetic data')
    parser.add_argument('--demo', action='store_true', help='Use synthetic example data (not real KT2 results)')
    parser.add_argument('--corpus', type=Path, help='JSONL chunks: chunk_id, document_id, text, optional metadata')
    parser.add_argument('--questions', type=Path, help='JSONL questions: id, query, gold_document_ids, split, filters')
    parser.add_argument('--split', choices=['all', 'dev', 'holdout'], default='all')
    parser.add_argument('--k1', type=float, default=1.5)
    parser.add_argument('--b', type=float, default=0.75)
    parser.add_argument('--output', type=Path, default=Path('benchmark/results.json'))
    args = parser.parse_args()
    if not (args.demo or (args.corpus and args.questions)):
        parser.error('Specify --demo or both --corpus and --questions')
    if args.demo:
        base = Path(__file__).resolve().parent
        corpus, questions = base/'demo_chunks.jsonl', base/'demo_questions.jsonl'
        print('DEMO MODE: synthetic data; scores are NOT real KT2 evidence')
    else:
        corpus, questions = args.corpus, args.questions
    chunks, queries = list(read_jsonl(corpus)), list(read_jsonl(questions))
    if args.split != 'all':
        queries = [q for q in queries if q.get('split') == args.split]
    if not queries:
        parser.error('No questions found for the selected split')
    if not 0 <= args.b <= 1 or args.k1 <= 0:
        parser.error('BM25 requires k1 > 0 and 0 <= b <= 1')
    report = run_benchmark(chunks, queries, args.k1, args.b, strict=(not args.demo and args.split == 'all'))
    has_unverified = any(q.get('annotation_status') == 'auto_candidates_unverified' for q in queries)
    report['mode'] = ('synthetic_demo' if args.demo else
                      'real_corpus_unverified_labels' if has_unverified else 'real_corpus')
    if has_unverified:
        print('WARNING: Gold labels are AUTOMATIC CANDIDATES, not human-verified. Metrics are preliminary.')
    report['corpus_path'] = str(corpus)
    report['questions_path'] = str(questions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    print('Per-query:')
    for item in report['results']:
        print(f"  {item['id']}: Recall@5={item['recall_at_5']:.3f}, RR={item['reciprocal_rank']:.3f}, "
              f"latency={item['latency_ms']:.3f} ms; top={','.join(x['document_id'] for x in item['ranked'])}")
    print(f'Report: {args.output}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError) as exc:
        print(f'Benchmark error: {exc}', file=sys.stderr)
        sys.exit(1)
