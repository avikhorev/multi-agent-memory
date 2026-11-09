"""Карантин для фрагментов недоверенного содержимого, похожих на инструкции.

Недоверенный текст (вывод инструментов, документы) — это данные, а не команды. Строка
задерживается, если в ней есть признак prompt injection: она обращается к агенту или ИИ,
велит игнорировать или переопределить правила, ссылается на системную власть или задаёт
поведение для будущих сессий. Обычные повелительные фразы («перешли лог», «отправь
протокол», «всегда ставь офис в копию») — это данные, их не трогаем.
Известные ограничения: простая атака без этих маркеров проходит; безобидная строка с
маркером («from now on the sync is on Thursday») блокируется. Обе цены измеряются.
"""
from __future__ import annotations

import re

# Признаки инструкции, адресованной модели. Регистр не важен (re.I).
# Группы по порядку: обращение к ассистенту/ИИ; «игнорируй правила/инструкции»;
# «игнорируй всё предыдущее»; «с этого момента» и «в будущих сессиях»;
# «новые инструкции» и «системный промпт»; прямой приказ «you must/should/will».
_INSTRUCTION = re.compile(
    r"\b(automated assistants?|ai (?:agents?|assistants?|systems?)|language models?|assistants? reading"
    r"|(?:ignore|disregard|forget|override)\b[^.\n]{0,40}\b(?:rules?|instructions?|polic(?:y|ies)|guidelines|configuration)"
    r"|(?:ignore|disregard)\s+(?:all |every |any )?(?:earlier|previous|prior|above)"
    r"|from now on|in (?:all )?(?:future|following) sessions?"
    r"|new instructions?|system (?:prompt|override|notice)"
    r"|you (?:must|should|will|are to))\b",
    re.I)

def fragments(text: str) -> list[str]:
    """Разбивает текст на строки (маркер списка не считается). Это единица карантина:
    строка с внедрённой инструкцией задерживается целиком, а не по предложениям."""
    return [ln for ln in (raw.strip().lstrip("-*").strip() for raw in text.split("\n")) if ln]

def split_untrusted(text: str) -> tuple[list[str], list[str]]:
    """Возвращает (оставленные фрагменты, задержанные в карантине фрагменты)."""
    kept, held = [], []
    for frag in fragments(text):
        (held if _INSTRUCTION.search(frag) else kept).append(frag)
    return kept, held
