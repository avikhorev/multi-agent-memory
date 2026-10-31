"""Memory systems behind one interface (docs/SCENARIO_FORMAT.md, section 8)."""
from __future__ import annotations

from mam.systems.base import MemorySystem
from mam.systems.baselines import FullHistory, SharedRagBm25, SlidingWindow
from mam.systems.ours import Ours
from mam.systems.summary import CachedSummary, LLMSummary, RollingSummary

NAMES = ("ours", "full_history", "sliding_window", "rolling_summary", "shared_rag_bm25")
ABLATIONS = frozenset({"validity", "scopes", "trust", "pinned_constraints"})
EXTRACTORS = ("oracle", "rules", "cache", "llm")


def create(name: str, *, limit: int = 2000, ablate=frozenset(), extractor: str = "oracle",
           cache_path=None, llm=None) -> MemorySystem:
    ablate = frozenset(ablate)
    if name not in NAMES:
        raise ValueError(f"unknown system: {name}")
    if extractor not in EXTRACTORS:
        raise ValueError(f"unknown extractor: {extractor}")
    if not ablate <= ABLATIONS:
        raise ValueError(f"unknown ablation: {sorted(ablate - ABLATIONS)}")
    if ablate and name != "ours":
        raise ValueError("ablations apply to 'ours' only")
    if name == "full_history":
        return FullHistory(limit)
    if name == "sliding_window":
        return SlidingWindow(limit)
    if name == "shared_rag_bm25":
        return SharedRagBm25(limit)
    if name == "rolling_summary":
        if extractor == "llm":
            if llm is None:
                raise ValueError("extractor 'llm' needs a client")
            return LLMSummary(limit, llm)
        if extractor == "cache":
            if cache_path is None:
                raise ValueError("extractor 'cache' needs cache_path")
            return CachedSummary(limit, cache_path)
        return RollingSummary(limit, extractor, cache_path)
    return Ours(limit, ablate, extractor, cache_path, llm)
