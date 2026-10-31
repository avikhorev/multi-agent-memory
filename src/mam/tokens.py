"""Offline token counter, calibrated against provider usage (docs/DECISIONS.md, D4).

A linear model over features of a few regular expressions. Deterministic, no
network, no dependencies. Weights come from results/pilot/token_counter_fit.json.
"""
import re

_WORD = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")
_DIGITS = re.compile(r"\d+")
_PUNCT = re.compile(r"[^\sA-Za-z0-9]")

_W_WORD = 1.187
_W_LONG = 0.658  # per letter beyond the sixth in a word
_W_CAPS = 0.845  # per letter of a word written in capitals (length > 1)
_W_DIGIT = 0.500
_W_PUNCT = 1.300


def count(text: str) -> int:
    words = _WORD.findall(text)
    total = (
        _W_WORD * len(words)
        + _W_LONG * sum(max(0, len(w) - 6) for w in words)
        + _W_CAPS * sum(len(w) for w in words if len(w) > 1 and w.isupper())
        + _W_DIGIT * sum(len(d) for d in _DIGITS.findall(text))
        + _W_PUNCT * len(_PUNCT.findall(text))
    )
    return round(total)
