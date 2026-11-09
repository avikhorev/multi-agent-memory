"""Оценки релевантности BM25; общие для базовой системы с поиском и для `ours`."""
from __future__ import annotations

import math
import re

# Токен — последовательность латинских букв/цифр в нижнем регистре.
_TOKEN = re.compile(r"[a-z0-9]+")
# Стандартные параметры BM25: K1 — насыщение частоты слова, B — сила нормировки на длину текста.
K1, B = 1.5, 0.75

def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())

def bm25_scores(query: str, texts: list[str]) -> list[float]:
    """Оценка каждого текста относительно запроса (больше — релевантнее); порядок как у texts.

    Идея: слово ценно, если оно редкое среди текстов (idf) и часто встречается в данном
    тексте (tf), но частота насыщается, а длинные тексты слегка штрафуются.
    """
    if not texts:
        return []
    toks = [tokenize(t) for t in texts]
    # Средняя длина текста; "or 1.0" защищает от деления на ноль, если все тексты пустые.
    avg = (sum(len(t) for t in toks) / len(toks)) or 1.0
    # df[w] — в скольких текстах встречается слово w.
    df: dict[str, int] = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    q = set(tokenize(query))
    out = []
    for t in toks:
        # tf[w] — сколько раз слово w встречается в этом тексте.
        tf: dict[str, int] = {}
        for w in t:
            tf[w] = tf.get(w, 0) + 1
        score = 0.0
        # Считаем только слова, общие для запроса и текста.
        for w in q & tf.keys():
            idf = math.log(1 + (len(texts) - df[w] + 0.5) / (df[w] + 0.5))
            score += idf * tf[w] * (K1 + 1) / (tf[w] + K1 * (1 - B + B * len(t) / avg))
        out.append(score)
    return out
