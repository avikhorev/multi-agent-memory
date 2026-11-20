"""Offline token counter, calibrated on the provider's data (docs/DECISIONS.md, D4).

Why it is needed: the context budget is measured in tokens, and the provider's real tokenizer
requires the network and dependencies. Here a linear model over features is used, which are
counted by several regular expressions. It is deterministic (the same text
always gives the same number), does not go to the network and has no dependencies. The weights were chosen
on the results of results/pilot/token_counter_fit.json.
"""
import re

# A word of Latin letters; a suffix with an apostrophe is allowed ("don't", "agent's").
_WORD = re.compile(r"[A-Za-z]+(?:'[a-z]+)?")
# Consecutive digits count as one number.
_DIGITS = re.compile(r"\d+")
# Any character that is not a space, not a Latin letter and not a digit (punctuation, non-Latin letters, etc.).
_PUNCT = re.compile(r"[^\sA-Za-z0-9]")

# Model weights: how many tokens each feature "costs".
_W_WORD = 1.187   # per word
_W_LONG = 0.658   # per letter beyond the sixth in a word (long words are split into parts)
_W_CAPS = 0.845   # per letter of a word written in capitals (length > 1)
_W_DIGIT = 0.500  # per digit
_W_PUNCT = 1.300  # per "other" character

def count(text: str) -> int:
    """Estimate of the number of tokens in a text (an integer, rounded)."""
    words = _WORD.findall(text)
    total = (
        _W_WORD * len(words)
        + _W_LONG * sum(max(0, len(w) - 6) for w in words)
        + _W_CAPS * sum(len(w) for w in words if len(w) > 1 and w.isupper())
        + _W_DIGIT * sum(len(d) for d in _DIGITS.findall(text))
        + _W_PUNCT * len(_PUNCT.findall(text))
    )
    return round(total)
