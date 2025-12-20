import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from bot.main import format_drawn_cards, format_tarot_answer
from core.tarot import ONE_CARD, THREE_CARD_SITUATION, orientation_label


def _build_drawn_cards(spread, reversed_indexes=None):
    reversed_indexes = reversed_indexes or set()
    drawn_cards = []
    for idx, position in enumerate(spread.positions):
        is_reversed = idx in reversed_indexes
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


def test_format_drawn_cards_single_spread():
    drawn_cards = _build_drawn_cards(ONE_CARD)
    formatted = format_drawn_cards(drawn_cards)

    assert formatted == "《カード》：カード1（正位置）"


def test_format_drawn_cards_keeps_order_and_positions():
    drawn_cards = _build_drawn_cards(THREE_CARD_SITUATION, reversed_indexes={1})
    formatted = format_drawn_cards(drawn_cards)

    assert (
        formatted
        == "《カード》：カード1（正位置） - 現在の状況、カード2（逆位置） - 障害や課題、カード3（正位置） - 未来の可能性"
    )


def test_format_tarot_answer_injects_card_line_once():
    drawn_cards = _build_drawn_cards(THREE_CARD_SITUATION, reversed_indexes={0, 2})
    card_line = format_drawn_cards(drawn_cards)
    answer = (
        "結論：状況は好転しそうです。\n\n理由：焦らず進めると良いでしょう。\n"
        "・行動1\n・行動2"
    )

    formatted = format_tarot_answer(answer, card_line=card_line)

    assert formatted.count("《カード》：") == 1
    lines = formatted.splitlines()
    assert lines[0] == "状況は好転しそうです。"
    assert card_line in formatted
    assert "・行動1" in formatted


def test_format_tarot_answer_overwrites_mismatched_card_line():
    drawn_cards = _build_drawn_cards(THREE_CARD_SITUATION, reversed_indexes={1})
    card_line = format_drawn_cards(drawn_cards)
    answer = (
        "引いたカード：バラバラな書き方でした\n"
        "結論：指針を守りましょう。\n・アクション1\n・アクション2"
    )

    formatted = format_tarot_answer(answer, card_line=card_line)

    assert formatted.count("《カード》：") == 1
    assert card_line in formatted
    assert "バラバラな書き方でした" not in formatted


def test_format_tarot_answer_removes_headings_and_merges_conclusion():
    drawn_cards = _build_drawn_cards(ONE_CARD)
    card_line = format_drawn_cards(drawn_cards)
    answer = (
        "【メインメッセージ】\n"
        "メインメッセージ\n"
        "引いたカード：ワンドの5（逆位置）\n"
        "理由：調和を意識しましょう。\n"
        "・周囲の声を丁寧に拾う。\n"
        "・焦らず段取りを整える。\n"
        "\n"
        "来年の仕事運は落ち着きを取り戻すでしょう。"
    )

    formatted = format_tarot_answer(answer, card_line=card_line)

    assert formatted.count("《カード》：") == 1
    assert "メインメッセージ" not in formatted
    assert formatted.splitlines()[-1].startswith("・")
    assert "まとめとして、来年の仕事運は落ち着きを取り戻すでしょう。" in formatted
