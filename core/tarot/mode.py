from __future__ import annotations

import re
from typing import Iterable

TRIGGERS: tuple[str, ...] = (
    "占って",
    "占い",
    "タロット",
    "カードを引いて",
    "カード引いて",
    "鑑定して",
    "リーディングして",
)

TAROT_LIKE_KEYWORDS: tuple[str, ...] = (
    "引いたカード",
    "正位置",
    "逆位置",
    "スプレッド",
    "大アルカナ",
    "小アルカナ",
    "ワンド",
    "カップ",
    "ソード",
    "ペンタクル",
)


def is_tarot_request(text: str) -> bool:
    if not text:
        return False

    lowered = text.lower()
    if lowered.startswith("/tarot"):
        return True

    if any(trigger in text for trigger in TRIGGERS):
        return True

    if "カード" in text and any(keyword in text for keyword in ("引い", "占い", "リーディング", "鑑定")):
        return True

    return False


def contains_tarot_like(text: str) -> bool:
    if not text:
        return False
    return any(keyword in text for keyword in TAROT_LIKE_KEYWORDS)


def strip_tarot_sentences(text: str, *, keywords: Iterable[str] | None = None) -> str:
    if not text:
        return ""

    use_keywords = tuple(keywords) if keywords is not None else TAROT_LIKE_KEYWORDS
    sentences = re.split(r"(?<=[。！？!?.])", text)
    filtered = [s for s in sentences if s and not any(k in s for k in use_keywords)]
    cleaned = "".join(filtered).strip()
    return cleaned
