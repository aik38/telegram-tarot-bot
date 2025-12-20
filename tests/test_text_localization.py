import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from bot.main import (
    build_tarot_theme_keyboard,
    build_upgrade_keyboard,
    get_start_text,
)
from bot.texts.i18n import t


def _extract_button_texts(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_ja_start_and_tarot_prompts_match_originals():
    expected_start = (
        "こんにちは、タロット占い＆お悩み相談 tarot_cat です🐈‍⬛\n"
        "ワンオラクルは1日2回まで無料でカードを引けます（/read1）。\n"
        "\n"
        "もっとじっくり占いたい方や、\n"
        "トークや相談を自由に使いたい方には7日／30日パスも用意しています。\n"
        "\n"
        "下のボタンから\n"
        "「🎩占い」または「💬相談」を選んでください。\n"
        "使い方は /help で確認できます。\n"
    )
    assert get_start_text("ja") == expected_start
    assert t("ja", "TAROT_THEME_PROMPT") == "🎩占いモードです。まずテーマを選んでください👇（恋愛/結婚/仕事/人生）"
    assert t("ja", "TAROT_THEME_SELECT_PROMPT") == "テーマを選んでください👇"
    assert _extract_button_texts(build_tarot_theme_keyboard(lang="ja")) == [
        "❤️恋愛",
        "💍結婚",
        "💼仕事",
        "🌉人生",
    ]
    assert _extract_button_texts(build_upgrade_keyboard(lang="ja")) == [
        "3枚で深掘り（有料）"
    ]


def test_en_start_and_tarot_prompts_are_localized():
    assert get_start_text("en").startswith("Hello, I'm tarot_cat for tarot readings and consultations.")
    assert t("en", "TAROT_THEME_PROMPT").startswith("🎩 Tarot mode.")
    assert t("en", "TAROT_THEME_SELECT_PROMPT").startswith("Please choose a theme")
    assert _extract_button_texts(build_tarot_theme_keyboard(lang="en")) == [
        "❤️ Love",
        "💍 Marriage",
        "💼 Work",
        "🌉 Life",
    ]
    assert _extract_button_texts(build_upgrade_keyboard(lang="en")) == [
        "3-card deep dive (paid)"
    ]


def test_unknown_language_falls_back_to_ja():
    assert t("unknown", "TAROT_THEME_PROMPT") == t("ja", "TAROT_THEME_PROMPT")
