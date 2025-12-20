import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from bot.main import build_tarot_messages, format_tarot_answer, format_drawn_cards
from core.tarot import ONE_CARD, THREE_CARD_SITUATION, orientation_label


def _build_drawn_cards(spread):
    drawn_cards = []
    for idx, position in enumerate(spread.positions):
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


def test_theme_prompts_include_love_focus():
    messages = build_tarot_messages(
        spread=THREE_CARD_SITUATION,
        user_query="恋愛について",
        drawn_cards=_build_drawn_cards(THREE_CARD_SITUATION),
        theme="love",
    )
    system_text = "\n".join(msg["content"] for msg in messages if msg["role"] == "system")

    assert "恋愛・関係性" in system_text
    assert "優しく示唆" in system_text


def test_theme_prompts_include_work_focus():
    messages = build_tarot_messages(
        spread=ONE_CARD,
        user_query="仕事について",
        drawn_cards=_build_drawn_cards(ONE_CARD),
        theme="work",
    )
    system_text = "\n".join(msg["content"] for msg in messages if msg["role"] == "system")

    assert "仕事・キャリア" in system_text
    assert "次の一手" in system_text


def test_theme_prompts_default_to_life():
    messages = build_tarot_messages(
        spread=ONE_CARD,
        user_query="人生について",
        drawn_cards=_build_drawn_cards(ONE_CARD),
        theme=None,
    )
    system_text = "\n".join(msg["content"] for msg in messages if msg["role"] == "system")

    assert "人生全体" in system_text
    assert "希望を持てる形" in system_text


def test_position_labels_are_injected_into_answer():
    drawn_cards = _build_drawn_cards(THREE_CARD_SITUATION)
    card_line = format_drawn_cards(drawn_cards)
    answer = "結論：前向きな流れです。\n理由：少しずつ整えていきましょう。\n・行動1\n・行動2"

    formatted = format_tarot_answer(
        answer,
        card_line=card_line,
        position_labels=("過去", "現在", "未来"),
    )

    assert "【現在】" in formatted
    assert "【過去】" in formatted
    assert "【未来】" in formatted


def test_tarot_prompts_are_localized_for_en():
    messages = build_tarot_messages(
        spread=ONE_CARD,
        user_query="Career check",
        drawn_cards=_build_drawn_cards(ONE_CARD),
        theme="work",
        lang="en",
    )
    system_text = "\n".join(msg["content"] for msg in messages if msg["role"] == "system")

    assert "Output rules:" in system_text
    assert "work/career" in system_text.lower()
    assert "出力ルール" not in system_text
