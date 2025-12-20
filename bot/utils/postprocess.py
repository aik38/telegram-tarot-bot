import re

from bot.texts.i18n import normalize_lang, t


def postprocess_llm_text(
    text: str,
    *,
    soft_limit: int = 2000,
    max_length: int = 2300,
    lang: str | None = None,
) -> str:
    """
    Normalize raw LLM output without changing its meaning.

    Steps:
    - Trim whitespace at the start/end of each line
    - Compress runs of blank lines
    - Soft-cut abnormally long outputs and append a polite notice
    """
    normalized = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    trimmed_lines = [line.strip() for line in normalized.split("\n")]
    normalized = "\n".join(trimmed_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()

    if len(normalized) <= max_length:
        return normalized

    cut = normalized[:soft_limit].rstrip()
    lang_code = normalize_lang(lang)
    note = t(lang_code, "POSTPROCESS_TRUNCATION_NOTE")
    return f"{cut}\n\n{note}"
