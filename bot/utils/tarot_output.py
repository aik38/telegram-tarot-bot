import re
from typing import Iterable, Sequence

from core.tarot.draws import orientation_label_by_lang


META_PHRASES = [
    "【メインメッセージ】",
    "メインメッセージ",
    "まとめとして",
    "結論として",
    "結論",
    "要するに",
    "最後に",
]

_CARD_LINE_PATTERN = re.compile(r"^(?:【?引いたカード】?|引いたカード|カード|《?カード》?)[：:]\s*(.+)$")
_INLINE_META_PATTERN = re.compile(
    r"(【?メインメッセージ】?|まとめとして|結論として|結論|最後に|要するに)[：:、,]?\s*",
    flags=re.IGNORECASE,
)
_BULLET_PATTERN = re.compile(r"^[・•\-]\s*(.+)$")
_BULLET_LABEL_PATTERN = re.compile(
    r"^(?:まず|次に|そして|その上で|まとめとして|要するに|結論として|結論|最後に)[：:、,]?\s*",
    flags=re.IGNORECASE,
)
_TIME_LABEL_PATTERN = re.compile(r"^【?\s*(過去|現在|未来)\s*】?[：:、,]?\s*", flags=re.IGNORECASE)
_TIME_AXIS_POSITION_ORDER: tuple[str, ...] = ("past", "present", "future")
_HEADING_LINE_PATTERN = re.compile(r"^【[^】]+】\s*$")


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


def _normalize_time_axis_line(text: str) -> str:
    cleaned = re.sub(r"^[0-9]+[\.．]\s*", "", text)
    cleaned = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "", cleaned)
    cleaned = _strip_meta_phrases(cleaned)
    cleaned = _TIME_LABEL_PATTERN.sub("", cleaned)
    if _HEADING_LINE_PATTERN.match(cleaned):
        return ""
    return cleaned.strip()


def _split_blocks(lines: Iterable[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line == "":
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _build_time_axis_card_line(
    card: dict[str, str] | None,
    *,
    card_line_prefix: str,
    lang: str,
) -> str:
    card_data = card.get("card", {}) if isinstance(card, dict) else {}
    lang_code = lang.lower()
    name = (
        card_data.get(f"name_{lang_code}")
        or card_data.get("name_en")
        or card_data.get("name_ja")
        or "不明なカード"
    )
    orientation_label = card_data.get(f"orientation_label_{lang_code}")
    if not orientation_label:
        orientation = (card_data.get("orientation") or "").lower()
        is_reversed = orientation == "reversed"
        orientation_label = orientation_label_by_lang(is_reversed, lang_code)
    orientation_suffix = f"（{orientation_label}）" if lang_code == "ja" else f" ({orientation_label})"
    return f"{card_line_prefix}{name}{orientation_suffix}"


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


def format_time_axis_tarot_answer(
    text: str,
    *,
    drawn_cards: Sequence[dict[str, str]],
    time_range_text: str = "前後3か月",
    caution_note: str | None = None,
    lang: str = "ja",
    card_line_prefix: str | None = None,
    time_scope_line: str | None = None,
) -> str:
    """
    Normalize a 3-card past/present/future reading into the mandated format.
    """
    lang_code = (lang or "ja").strip().lower().replace("_", "-")
    effective_card_line_prefix = card_line_prefix or ("《カード》：" if lang_code == "ja" else "《Card》: ")
    working = (text or "").rstrip()
    attached_caution = None
    if caution_note:
        caution_idx = working.rfind(caution_note)
        if caution_idx != -1 and working[caution_idx:].strip() == caution_note:
            attached_caution = caution_note
            working = working[:caution_idx].rstrip()

    normalized_lines: list[str] = []
    for raw_line in working.splitlines():
        line = raw_line.strip()
        if not line:
            normalized_lines.append("")
            continue

        line = _normalize_time_axis_line(line)
        if not line:
            continue

        normalized_lines.append(line)

    compressed_lines = _compress_blank_lines(normalized_lines)
    blocks = _split_blocks(compressed_lines)
    while len(blocks) < 3:
        blocks.append([])
    if len(blocks) > 3:
        trailing = [ln for block in blocks[3:] for ln in block if ln]
        blocks = blocks[:3]
        if trailing:
            if blocks[2]:
                blocks[2].append("")
            blocks[2].extend(trailing)

    redistributed_bullets: list[str] = []
    cleaned_blocks: list[list[str]] = []
    for idx, block in enumerate(blocks[:3]):
        new_block: list[str] = []
        for line in block:
            bullet_match = _BULLET_PATTERN.match(line)
            if bullet_match:
                normalized_bullet = _normalize_bullet(line)
                if normalized_bullet:
                    redistributed_bullets.append(normalized_bullet)
                continue
            new_block.append(line)
        cleaned_blocks.append(_compress_blank_lines(new_block))

    future_bullets = [b for b in redistributed_bullets if b][:3]
    if time_scope_line is None:
        if time_range_text:
            if lang_code == "ja":
                time_scope_line = f"{time_range_text}ほどの流れとして読みます。"
            elif lang_code.startswith("pt"):
                time_scope_line = f"Lendo o fluxo de cerca de {time_range_text}."
            else:
                time_scope_line = f"Reading the flow over about {time_range_text}."
        else:
            time_scope_line = ""
    if time_scope_line:
        first_block = cleaned_blocks[0]
        if time_scope_line not in first_block:
            cleaned_blocks[0] = [time_scope_line] + first_block

    card_lookup = {item.get("id"): item for item in drawn_cards if isinstance(item, dict)}
    ordered_cards: list[dict[str, str] | None] = []
    for position_id in _TIME_AXIS_POSITION_ORDER:
        if position_id in card_lookup:
            ordered_cards.append(card_lookup[position_id])
    for item in drawn_cards:
        if item not in ordered_cards and len(ordered_cards) < 3:
            ordered_cards.append(item)
    while len(ordered_cards) < 3:
        ordered_cards.append({})

    final_lines: list[str] = []
    for idx, card in enumerate(ordered_cards[:3]):
        final_lines.append(
            _build_time_axis_card_line(
                card,
                card_line_prefix=effective_card_line_prefix,
                lang=lang_code,
            )
        )
        body_lines = cleaned_blocks[idx] if idx < len(cleaned_blocks) else []
        final_lines.extend(body_lines)

        if idx == 2:
            if body_lines and future_bullets:
                final_lines.append("")
            final_lines.extend(future_bullets)

        if idx < 2 and final_lines and final_lines[-1] != "":
            final_lines.append("")

    final_lines = _compress_blank_lines(final_lines)
    if attached_caution:
        if final_lines:
            final_lines.append("")
        final_lines.append(attached_caution)

    return "\n".join(final_lines)
