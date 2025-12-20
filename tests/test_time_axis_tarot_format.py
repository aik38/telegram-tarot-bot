import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from bot.main import CAUTION_NOTE, build_tarot_messages
from bot.utils.tarot_output import format_time_axis_tarot_answer
from core.tarot import THREE_CARD_TIME_AXIS, orientation_label


def _build_drawn_cards():
    drawn_cards = []
    for idx, position in enumerate(THREE_CARD_TIME_AXIS.positions):
        is_reversed = idx % 2 == 1
        drawn_cards.append(
            {
                "id": position.id,
                "label_ja": position.label_ja,
                "meaning_ja": position.meaning_ja,
                "card": {
                    "id": f"card_{idx + 1}",
                    "name_ja": f"カード{idx + 1}",
                    "name_en": f"Card {idx + 1}",
                    "orientation": "reversed" if is_reversed else "upright",
                    "orientation_label_ja": orientation_label(is_reversed),
                    "keywords_ja": [],
                },
            }
        )
    return drawn_cards


def test_time_axis_formatter_orders_cards_and_limits_bullets():
    drawn_cards = _build_drawn_cards()
    raw = (
        "過去は手放しのタイミングでした。\n"
        "・過去の手放しを意識する\n"
        "現在は慎重さが勝ち、静かに整理しています。\n"
        "未来には視界が開けていきます。\n"
        "・視野を広げる\n"
        "・急ぎすぎない\n"
        "・助けを借りる\n"
        "・余白を残す\n\n"
        f"{CAUTION_NOTE}"
    )

    formatted = format_time_axis_tarot_answer(
        raw,
        drawn_cards=drawn_cards,
        time_range_text="前後3か月",
        caution_note=CAUTION_NOTE,
    )

    lines = formatted.splitlines()
    card_lines = [line for line in lines if line.startswith("《カード》：")]
    assert card_lines == [
        "《カード》：カード1（正位置）",
        "《カード》：カード2（逆位置）",
        "《カード》：カード3（正位置）",
    ]
    assert any("前後3か月" in line for line in lines)
    third_index = lines.index(card_lines[2])
    assert all(not line.startswith("・") for line in lines[:third_index])
    future_bullets = [line for line in lines[third_index + 1 :] if line.startswith("・")]
    assert len(future_bullets) == 3
    assert formatted.endswith(CAUTION_NOTE)


def test_time_axis_prompt_mentions_structure_and_scope():
    drawn_cards = _build_drawn_cards()
    messages = build_tarot_messages(
        spread=THREE_CARD_TIME_AXIS,
        user_query="流れを知りたいです",
        drawn_cards=drawn_cards,
        theme="love",
    )

    system_text = "\n".join(msg["content"] for msg in messages if msg["role"] == "system")

    assert "過去・現在・未来" in system_text
    assert "前後3か月" in system_text
    assert "《カード》：" in system_text


def test_time_axis_finalizer_enforces_headings_and_bullet_rules():
    drawn_cards = _build_drawn_cards()
    raw = (
        "【メインメッセージ】\n"
        "過去は手放しのときでした。\n"
        "・過去の手放しを振り返る\n"
        "\n"
        "まとめとして、現在は静かに整理しています。\n"
        "・今の一歩を丁寧に\n"
        "結論: 落ち着きが戻りつつあります。\n"
        "\n"
        "最後に、未来には光が差します。\n"
        "・視野を広げる\n"
        "・深呼吸して待つ\n"
        "・仲間を頼る\n"
        "・余白を残す\n"
    )

    formatted = format_time_axis_tarot_answer(
        raw,
        drawn_cards=drawn_cards,
        time_range_text="前後3か月",
        caution_note=CAUTION_NOTE,
    )

    lines = formatted.splitlines()
    card_lines = [line for line in lines if line.startswith("《カード》：")]
    assert len(card_lines) == 3
    banned = ("まとめとして", "結論", "最後に", "【")
    assert all(all(b not in line for b in banned) for line in lines)

    third_idx = lines.index(card_lines[2])
    bullet_lines = [line for line in lines if line.startswith("・")]
    assert len(bullet_lines) == 3
    assert all("・" not in line for line in lines[:third_idx])
