from typing import Tuple

from bot.texts.i18n import normalize_lang, t
from bot.texts.ja import MAX_QUESTION_CHARS


def validate_question_text(
    text: str | None, *, is_text: bool = True, lang: str | None = None
) -> Tuple[bool, str | None]:
    lang_code = normalize_lang(lang)
    if not is_text:
        return False, t(lang_code, "NON_TEXT_MESSAGE_TEXT")

    if text is None:
        return False, t(lang_code, "NON_TEXT_MESSAGE_TEXT")

    cleaned = text.strip()
    if not cleaned:
        return False, t(lang_code, "EMPTY_QUESTION_TEXT")

    if len(cleaned) > MAX_QUESTION_CHARS:
        return False, t(lang_code, "LONG_QUESTION_TEXT")

    return True, None
