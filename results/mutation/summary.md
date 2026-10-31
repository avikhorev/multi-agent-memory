# Mutation pass over the structured memory and the quarantine filter

Tool: mutmut 3.8.1 (`make mutation`), files `src/mam/systems/ours.py` and `src/mam/guard.py`, tests `tests/unit/`.

| Pass | Mutants | Killed | Survived |
|---|---|---|---|
| 1: tests as written for the code | 489 | 334 | 155 |
| 2: after tests for trace content, trust, budget edges, ranking | 489 | 469 | 20 |
| 3: after tests for hidden keys, note-derived text, known facts, fragments | 489 | 479 | 10 |

All 10 survivors of the last pass behave like the original code (equivalent mutants):

- `x__norm__mutmut_2`: joiner of whitespace-split pieces: both sides are normalised the same way
- `x__norm__mutmut_7`: upper instead of lower case: both sides are normalised the same way
- `__init____mutmut_1`: default extractor name: the factory always passes the extractor
- `__init____mutmut_2`: default extractor name: the factory always passes the extractor
- `__init____mutmut_19`: initial trace value: it is reset at the start of every read
- `_ingest__mutmut_11`: None instead of False for the wants_known default: both are falsy
- `_ingest__mutmut_32`: None instead of False for require_trusted: both are falsy
- `known_lines__mutmut_9`: `or True` after a condition whose false branch resolves an empty list
- `_resolve__mutmut_10`: initial latest time 1 instead of 0: only shifts the time given to the first undated fact
- `_fact_items__mutmut_20`: len(cur) >= 1 instead of > 1: a group of one gives the same single item
