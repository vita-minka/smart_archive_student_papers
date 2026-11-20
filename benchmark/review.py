"""Export human-checked document relevance from the review worksheet.

No automatic approval is performed. An empty/unknown judgment is an error.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path


def export_review(input_path, original_path, manifest_path, output_path, assistant_prechecked=False, decision_column=None):
    with input_path.open(encoding='utf-8-sig', newline='') as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError('Review worksheet is empty')
    original = [json.loads(line) for line in original_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(original) < 20:
        raise ValueError('Expected 20 or more original questions')
    questions = {q['id']: q for q in original}
    docs = {m['document_id'] for m in json.loads(manifest_path.read_text(encoding='utf-8')) if m['chunks'] > 0}
    if decision_column is None:
        decision_column = 'assistant_decision' if assistant_prechecked else 'human_verified'
    if decision_column not in ('human_verified', 'assistant_decision', 'relevance_decision'):
        raise ValueError('Unsupported decision column')
    if decision_column not in rows[0]:
        raise ValueError(f'Missing column: {decision_column}')
    decisions = defaultdict(dict)
    for line_number, row in enumerate(rows, 2):
        qid = (row.get('question') or '').strip()
        did = (row.get('document_id') or '').strip()
        decision = (row.get(decision_column) or '').strip().upper()
        if qid not in questions or did not in docs:
            raise ValueError(f'CSV line {line_number}: unknown question or document ID ({qid}, {did})')
        if (row.get('query') or '').strip() != questions[qid]['query']:
            raise ValueError(f'CSV line {line_number}: query does not match {qid}')
        if decision not in ('YES', 'NO'):
            raise ValueError(f'CSV line {line_number}: {decision_column} must be YES or NO (found {decision or "blank"})')
        if did in decisions[qid]:
            raise ValueError(f'CSV line {line_number}: duplicate pair {qid} / {did}')
        decisions[qid][did] = decision
    verified=[]
    for q in original:
        qid=q['id']
        labels=sorted(did for did,decision in decisions[qid].items() if decision=='YES')
        if len(labels)<3:
            raise ValueError(f'{qid}: only {len(labels)} confirmed relevant documents (need >= 3). Add reviewed documents before exporting')
        verified.append({**{k:v for k,v in q.items() if k!='annotation_status'},'gold_document_ids':labels,
                         'annotation_status':('human_verified' if decision_column == 'human_verified' else 'preliminary_unverified')})
    output_path.parent.mkdir(parents=True,exist_ok=True)
    with output_path.open('w',encoding='utf-8') as output:
        for q in verified:output.write(json.dumps(q,ensure_ascii=False)+'\n')
    return len(verified)


def main():
    parser=argparse.ArgumentParser(description='Validate reviewer decisions and export verified KT2 labels')
    parser.add_argument('--input',type=Path,default=Path('benchmark/review_for_confirmation.csv'))
    parser.add_argument('--questions',type=Path,default=Path('benchmark/questions.jsonl'))
    parser.add_argument('--manifest',type=Path,default=Path('corpus/manifest.json'))
    parser.add_argument('--export',type=Path,default=Path('benchmark/questions_verified.jsonl'))
    parser.add_argument('--assistant-prechecked', action='store_true', help='Use assistant_decision (legacy preliminary input)')
    parser.add_argument('--decision-column', choices=['human_verified','assistant_decision','relevance_decision'], help='Column with YES/NO decisions; only human_verified means reviewer confirmation')
    args=parser.parse_args()
    try:
        count=export_review(args.input,args.questions,args.manifest,args.export,assistant_prechecked=args.assistant_prechecked,decision_column=args.decision_column)
    except (ValueError,KeyError,OSError,json.JSONDecodeError) as exc:
        parser.exit(1,f'Validation error: {exc}\n')
    column = args.decision_column or ('assistant_decision' if args.assistant_prechecked else 'human_verified')
    status = 'human-verified' if column == 'human_verified' else 'preliminary, not human-verified'
    print(f'Exported {count} questions: {args.export} (status: {status})')

if __name__=='__main__':main()
