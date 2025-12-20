import re
from typing import Iterable


META_PHRASES = [
    "【メインメッセージ】",
    "メインメッセージ",
    "まとめとして",
    "結論として",
    "要するに",
]

_CARD_LINE_PATTERN = re.compile(r"^(?:【?引いたカード】?|引いたカード|カード|《?カード》?)[：:]\s*(.+)$")
_INLINE_META_PATTERN = re.compile(
    r"(【?メインメッセージ】?|まとめとして|結論として|要するに)[：:、,]?\s*", flags=re.IGNORECASE
)
_BULLET_PATTERN = re.compile(r"^[・•\-]\s*(.+)$")
_BULLET_LABEL_PATTERN = re.compile(
    r"^(?:まず|次に|そして|その上で|まとめとして|要するに|結論として)[：:、,]?\s*", flags=re.IGNORECASE
)


def _strip_meta_phrases(text: str) -> str:
    cleaned = _INLINE_META_PATTERN.sub("", text)
    for phrase in META_PHRASES:
        cleaned = cleaned.replace(phrase, "")
    return cleaned


def _compress_blank_lines(lines: Iterable[str]) -> list[str]:
    compressed: list[str] = []
    for line in lines:
        if line == "":
            if compressed and compressed[-1] == "":
                continue
            compressed.append("")
            continue
        compressed.append(line)

    while compressed and compressed[0] == "":
        compressed.pop(0)
    while compressed and compressed[-1] == "":
        compressed.pop()
    return compressed


def _normalize_bullet(text: str) -> str:
    body = _BULLET_PATTERN.sub(r"\1", text).strip()
    body = _BULLET_LABEL_PATTERN.sub("", body).strip()
    return f"・{body}" if body else ""


def finalize_tarot_answer(
    text: str,
    *,
    card_line_prefix: str = "《カード》：",
    caution_note: str | None = None,
) -> str:
    """
    Normalize tarot answer text immediately before sending to the user.
    """
    if not text:
        return ""

    working = text.rstrip()
    attached_caution = None
    if caution_note:
        caution_idx = working.rfind(caution_note)
        if caution_idx != -1 and working[caution_idx:].strip() == caution_note:
            attached_caution = caution_note
            working = working[:caution_idx].rstrip()

    intro_lines: list[str] = []
    explanation_lines: list[str] = []
    trailing_after_bullets: list[str] = []
    bullets: list[str] = []
    card_line = None
    seen_card = False
    bullets_seen = False

    for raw_line in working.splitlines():
        line = raw_line.strip()
        if not line:
            target = trailing_after_bullets if bullets_seen else explanation_lines if seen_card else intro_lines
            target.append("")
            continue

        line = re.sub(r"^[0-9]+[\.．]\s*", "", line)
        line = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "", line)
        line = _strip_meta_phrases(line).strip()
        if not line:
            continue

        card_match = _CARD_LINE_PATTERN.match(line)
        has_card_prefix = card_line_prefix in line
        if card_match or has_card_prefix:
            if card_line is None:
                content = card_match.group(1).strip() if card_match else line.split(card_line_prefix, 1)[-1].strip()
                card_line = f"{card_line_prefix}{content}"
            seen_card = True
            bullets_seen = False
            continue

        bullet_match = _BULLET_PATTERN.match(line)
        if bullet_match:
            normalized_bullet = _normalize_bullet(line)
            if normalized_bullet:
                bullets.append(normalized_bullet)
                bullets_seen = True
            continue

        target = trailing_after_bullets if bullets_seen else explanation_lines if seen_card else intro_lines
        target.append(line)

    bullets = [b for b in bullets if b][:4]
    intro_lines = _compress_blank_lines(intro_lines)
    explanation_lines = _compress_blank_lines(explanation_lines)

    final_lines: list[str] = []
    final_lines.extend(intro_lines)
    if final_lines and final_lines[-1] != "":
        final_lines.append("")

    if card_line:
        final_lines.append(card_line)
        if explanation_lines or bullets:
            final_lines.append("")

    final_lines.extend(explanation_lines)
    if explanation_lines and bullets:
        final_lines.append("")

    if bullets:
        if len(bullets) > 1 or (len(bullets) == 1 and bullets[0]):
            final_lines.extend(bullets)

    final_lines = _compress_blank_lines(final_lines)
    if attached_caution:
        if final_lines:
            final_lines.append("")
        final_lines.append(attached_caution)

    return "\n".join(final_lines)
