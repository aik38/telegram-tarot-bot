from typing import Tuple

from bot.texts.ja import (
    EMPTY_QUESTION_TEXT,
    LONG_QUESTION_TEXT,
    MAX_QUESTION_CHARS,
    NON_TEXT_MESSAGE_TEXT,
)


def validate_question_text(text: str | None, *, is_text: bool = True) -> Tuple[bool, str | None]:
    if not is_text:
        return False, NON_TEXT_MESSAGE_TEXT

    if text is None:
        return False, NON_TEXT_MESSAGE_TEXT

    cleaned = text.strip()
    if not cleaned:
        return False, EMPTY_QUESTION_TEXT

    if len(cleaned) > MAX_QUESTION_CHARS:
        return False, LONG_QUESTION_TEXT

    return True, None
