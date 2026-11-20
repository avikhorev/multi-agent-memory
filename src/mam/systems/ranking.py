"""BM25 relevance scores; shared by the baseline system with search and by `ours`."""
from __future__ import annotations

import math
import re

# A token is a sequence of Latin letters/digits in lower case.
_TOKEN = re.compile(r"[a-z0-9]+")
# Standard BM25 parameters: K1 — saturation of the word frequency, B — strength of the normalization by text length.
K1, B = 1.5, 0.75

def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())

def bm25_scores(query: str, texts: list[str]) -> list[float]:
    """Score of each text relative to the query (higher means more relevant); the order is the same as texts.

    Idea: a word is valuable if it is rare among the texts (idf) and often occurs in the given
    text (tf), but the frequency saturates, and long texts are penalized slightly.
    """
    if not texts:
        return []
    toks = [tokenize(t) for t in texts]
    # Average text length; "or 1.0" protects against division by zero if all texts are empty.
    avg = (sum(len(t) for t in toks) / len(toks)) or 1.0
    # df[w] — in how many texts the word w occurs.
    df: dict[str, int] = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    q = set(tokenize(query))
    out = []
    for t in toks:
        # tf[w] — how many times the word w occurs in this text.
        tf: dict[str, int] = {}
        for w in t:
            tf[w] = tf.get(w, 0) + 1
        score = 0.0
        # Count only the words shared by the query and the text.
        for w in q & tf.keys():
            idf = math.log(1 + (len(texts) - df[w] + 0.5) / (df[w] + 0.5))
            score += idf * tf[w] * (K1 + 1) / (tf[w] + K1 * (1 - B + B * len(t) / avg))
        out.append(score)
    return out
