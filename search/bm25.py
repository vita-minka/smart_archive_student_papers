"""Independent BM25 implementation; no third-party search engine."""
import math
import re
import unicodedata
from collections import Counter, defaultdict


def tokenize(text):
    return re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', text).lower(), flags=re.UNICODE)


class BM25Index:
    def __init__(self, chunks, k1=1.5, b=0.75):
        self.k1, self.b = float(k1), float(b)
        self.chunks = {str(c['chunk_id']): c for c in chunks}
        if len(self.chunks) != len(chunks):
            raise ValueError('Duplicate chunk_id')
        self.postings = defaultdict(dict)
        self.length = {}
        for cid, c in self.chunks.items():
            terms = Counter(tokenize(c['text']))
            self.length[cid] = sum(terms.values())
            for term, tf in terms.items():
                self.postings[term][cid] = tf
        self.N = len(self.chunks)
        self.avgdl = sum(self.length.values()) / self.N if self.N else 0
        self.df = {term: len(items) for term, items in self.postings.items()}

    def search(self, query, top_k=5, filters=None):
        if not self.N or not self.avgdl or not query.strip() or top_k <= 0:
            return []
        filters = filters or {}
        scores = defaultdict(float)
        for term in set(tokenize(query)):
            if term not in self.postings:
                continue
            df = self.df[term]
            idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
            for cid, tf in self.postings[term].items():
                chunk = self.chunks[cid]
                if any(chunk.get(key) != val for key, val in filters.items() if val is not None):
                    continue
                norm = tf + self.k1 * (1 - self.b + self.b * self.length[cid] / self.avgdl)
                scores[cid] += idf * tf * (self.k1 + 1) / norm
        ordered = sorted(scores, key=lambda cid: (-scores[cid], cid))
        seen = set()
        output = []
        for cid in ordered:
            docid = str(self.chunks[cid]['document_id'])
            if docid not in seen:
                seen.add(docid)
                output.append({'document_id': docid, 'chunk_id': cid, 'score': round(scores[cid], 8)})
            if len(output) == top_k:
                break
        return output
