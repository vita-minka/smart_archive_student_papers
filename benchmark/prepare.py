"""Prepare a reproducible corpus and a gold-label worksheet for KT2.

Requires only standard library for .txt/.md; PDF requires pymupdf or pypdf.
"""
import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


COLUMNS = ['id', 'split', 'query', 'gold_document_ids', 'filters', 'annotation_note']


def iter_pages(path):
    if path.suffix.lower() in ('.txt', '.md'):
        yield 1, path.read_text(encoding='utf-8-sig')
        return
    if path.suffix.lower() == '.pdf':
        try:
            import fitz
            with fitz.open(path) as doc:
                for i, page in enumerate(doc, 1):
                    yield i, page.get_text(sort=True)
            return
        except ImportError:
            pass
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            for i, page in enumerate(reader.pages, 1):
                yield i, page.extract_text() or ''
            return
        except ImportError as e:
            raise RuntimeError('PDF requires one package: python3 -m pip install pymupdf (or pypdf)') from e
    raise ValueError(f'Unsupported file type: {path}')


def make_chunks(text, max_words=180, overlap=35):
    words = text.split()
    if not words:
        return []
    step = max_words - overlap
    return [' '.join(words[start:start + max_words]) for start in range(0, len(words), step) if words[start:start + max_words]]


def build_corpus(source_dir, output_dir):
    if not source_dir.is_dir():
        raise ValueError(f'No input directory: {source_dir}')
    paths = sorted((p for p in source_dir.rglob('*') if p.is_file() and p.suffix.lower() in ('.txt', '.md', '.pdf')),
                   key=lambda p: p.relative_to(source_dir).as_posix())
    if not paths:
        raise ValueError('No .pdf, .txt or .md documents found')
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest, chunks, warnings = [], [], []
    for path in paths:
        raw = path.read_bytes()
        sha = hashlib.sha256(raw).hexdigest()
        rel = path.relative_to(source_dir).as_posix()
        docid = 'doc-' + hashlib.sha256(rel.encode('utf-8')).hexdigest()[:12]
        page_count = 0
        doc_chunks = 0
        try:
            for page_no, page_text in iter_pages(path):
                page_count += 1
                for seq, chunk_text in enumerate(make_chunks(page_text), 1):
                    chunks.append({'chunk_id': f'{docid}-p{page_no:04d}-c{seq:03d}', 'document_id': docid,
                                   'text': chunk_text, 'page': page_no, 'title': path.stem, 'source': rel})
                    doc_chunks += 1
        except Exception as e:
            warnings.append(f'{rel}: {e}')
            continue
        if not doc_chunks:
            warnings.append(f'{rel}: NO EXTRACTABLE TEXT (scanned PDF? OCR is not included)')
        manifest.append({'document_id': docid, 'source': rel, 'title': path.stem, 'sha256': sha,
                         'pages': page_count, 'chunks': doc_chunks})
    with (output_dir / 'chunks.jsonl').open('w', encoding='utf-8') as out:
        for c in chunks:
            out.write(json.dumps(c, ensure_ascii=False) + '\n')
    with (output_dir / 'manifest.json').open('w', encoding='utf-8') as out:
        json.dump(manifest, out, ensure_ascii=False, indent=2)
    with (output_dir / 'document_ids.csv').open('w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=['document_id', 'title', 'source', 'chunks'])
        writer.writeheader()
        for doc in manifest:
            writer.writerow({key: doc[key] for key in writer.fieldnames})
    return manifest, chunks, warnings


def write_worksheet(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError(f'Worksheet already exists, refusing overwrite: {path}')
    with path.open('w', newline='', encoding='utf-8-sig') as out:
        writer = csv.DictWriter(out, fieldnames=COLUMNS)
        writer.writeheader()
        for i in range(1, 21):
            writer.writerow({'id': f'q{i:02d}', 'split': 'dev' if i <= 10 else 'holdout',
                             'query': '', 'gold_document_ids': '', 'filters': '{}', 'annotation_note': ''})


def export_gold(worksheet, manifest, output):
    valid_ids = {str(doc['document_id']) for doc in json.loads(manifest.read_text(encoding='utf-8')) if doc['chunks'] > 0}
    with worksheet.open(newline='', encoding='utf-8-sig') as source:
        rows = list(csv.DictReader(source))
    if len(rows) < 20:
        raise ValueError(f'Expected at least 20 question rows, found {len(rows)}')
    questions, ids = [], set()
    for line, row in enumerate(rows, 2):
        qid = (row.get('id') or '').strip()
        query = (row.get('query') or '').strip()
        split = (row.get('split') or '').strip()
        if not qid or qid in ids or not query:
            raise ValueError(f'CSV line {line}: missing/duplicate question ID or empty query')
        ids.add(qid)
        if split not in ('dev', 'holdout'):
            raise ValueError(f'CSV line {line}: split must be dev or holdout')
        gold = [s.strip() for s in re.split(r'[;,]', row.get('gold_document_ids') or '') if s.strip()]
        if len(gold) < 3 or len(set(gold)) != len(gold):
            raise ValueError(f'CSV line {line}: need 3+ distinct gold document IDs')
        unknown = set(gold) - valid_ids
        if unknown:
            raise ValueError(f'CSV line {line}: unknown or empty documents: {sorted(unknown)}')
        filters = json.loads(row.get('filters') or '{}')
        if not isinstance(filters, dict):
            raise ValueError(f'CSV line {line}: filters must be JSON object')
        questions.append({'id': qid, 'split': split, 'query': query, 'gold_document_ids': gold, 'filters': filters})
    if not any(q['split'] == 'holdout' for q in questions) or not any(q['split'] == 'dev' for q in questions):
        raise ValueError('Need both dev and holdout queries')
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', encoding='utf-8') as out:
        for q in questions:
            out.write(json.dumps(q, ensure_ascii=False) + '\n')
    return len(questions)


def main():
    parser = argparse.ArgumentParser(description='Import real documents and prepare KT2 gold annotations')
    sub = parser.add_subparsers(dest='action', required=True)
    imp = sub.add_parser('import', help='Extract page-aware chunks from documents')
    imp.add_argument('--input', type=Path, default=Path('corpus/documents'))
    imp.add_argument('--output', type=Path, default=Path('corpus'))
    worksheet = sub.add_parser('worksheet', help='Generate 20 blank dev/holdout question rows')
    worksheet.add_argument('--output', type=Path, default=Path('benchmark/questions_to_fill.csv'))
    export = sub.add_parser('export', help='Validate human-annotated CSV and export gold JSONL')
    export.add_argument('--input', type=Path, default=Path('benchmark/questions_to_fill.csv'))
    export.add_argument('--manifest', type=Path, default=Path('corpus/manifest.json'))
    export.add_argument('--output', type=Path, default=Path('benchmark/questions.jsonl'))
    args = parser.parse_args()
    try:
        if args.action == 'import':
            documents, chunks, warnings = build_corpus(args.input, args.output)
            print(f'Imported {len(documents)} documents, {len(chunks)} chunks. ID map: {args.output}/document_ids.csv')
            for warning in warnings:
                print('WARNING:', warning)
            if not chunks:
                raise ValueError('No extractable text; cannot benchmark')
        elif args.action == 'worksheet':
            write_worksheet(args.output)
            print(f'Created 20 blank questions: {args.output}')
        else:
            count = export_gold(args.input, args.manifest, args.output)
            print(f'Exported {count} validated queries to {args.output}')
    except (ValueError, RuntimeError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f'Error: {exc}\n')


if __name__ == '__main__':
    main()
