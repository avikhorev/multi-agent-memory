"""BM25 relevance scores, shared by the retrieval baseline and by `ours`."""
from __future__ import annotations

import math
import re

_TOKEN = re.compile(r"[a-z0-9]+")
K1, B = 1.5, 0.75


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def bm25_scores(query: str, texts: list[str]) -> list[float]:
    if not texts:
        return []
    toks = [tokenize(t) for t in texts]
    avg = (sum(len(t) for t in toks) / len(toks)) or 1.0
    df: dict[str, int] = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    q = set(tokenize(query))
    out = []
    for t in toks:
        tf: dict[str, int] = {}
        for w in t:
            tf[w] = tf.get(w, 0) + 1
        score = 0.0
        for w in q & tf.keys():
            idf = math.log(1 + (len(texts) - df[w] + 0.5) / (df[w] + 0.5))
            score += idf * tf[w] * (K1 + 1) / (tf[w] + K1 * (1 - B + B * len(t) / avg))
        out.append(score)
    return out
