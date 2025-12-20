import re


def postprocess_llm_text(
    text: str,
    *,
    soft_limit: int = 2000,
    max_length: int = 2300,
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
    note = (
        "（文章がとても長かったため途中までお届けしました。続きが必要でしたら、"
        "もう一度聞いてくださいね。）"
    )
    return f"{cut}\n\n{note}"
