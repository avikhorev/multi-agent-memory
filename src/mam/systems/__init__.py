"""Системы памяти за одним интерфейсом (docs/SCENARIO_FORMAT.md, раздел 8)."""
from __future__ import annotations

from mam.systems.base import MemorySystem
from mam.systems.baselines import FullHistory, SharedRagBm25, SlidingWindow
from mam.systems.ours import Ours
from mam.systems.summary import CachedSummary, LLMSummary, RollingSummary

# Допустимые имена систем: наша и четыре базовых для сравнения.
NAMES = ("ours", "full_history", "sliding_window", "rolling_summary", "shared_rag_bm25")
# Что можно отключать в нашей системе, чтобы измерить вклад каждого механизма (абляции).
ABLATIONS = frozenset({"validity", "scopes", "trust", "pinned_constraints"})
# Способы извлекать факты из записей: эталон сценария, правила, кеш, живая модель.
EXTRACTORS = ("oracle", "rules", "cache", "llm")

def create(name: str, *, limit: int = 2000, ablate=frozenset(), extractor: str = "oracle",
           cache_path=None, llm=None) -> MemorySystem:
    """Фабрика систем памяти. limit — бюджет контекста в токенах.

    Все параметры проверяются до создания, чтобы опечатка в конфигурации
    падала сразу, а не посреди долгого прогона.
    """
    ablate = frozenset(ablate)
    if name not in NAMES:
        raise ValueError(f"unknown system: {name}")
    if extractor not in EXTRACTORS:
        raise ValueError(f"unknown extractor: {extractor}")
    if not ablate <= ABLATIONS:
        raise ValueError(f"unknown ablation: {sorted(ablate - ABLATIONS)}")
    if ablate and name != "ours":
        # Абляции — это отключение частей именно нашей системы; у базовых частей нет.
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
