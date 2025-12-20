import re
from types import SimpleNamespace

from bot import main
from bot.texts import en, ja, pt
from core.db import get_user_lang


def test_japanese_texts_stable() -> None:
    assert ja.START_TEXT == (
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
    assert ja.UPGRADE_BUTTON_TEXT == "3枚で深掘り（有料）"
    assert ja.TAROT_THEME_PROMPT == "🎩占いモードです。まずテーマを選んでください👇（恋愛/結婚/仕事/人生）"


def test_no_japanese_in_translated_texts() -> None:
    jp_chars = re.compile(r"[ぁ-んァ-ン一-龯]")
    for name, texts in [("en", en.TEXTS), ("pt", pt.TEXTS)]:
        for key, value in texts.items():
            if isinstance(value, str):
                assert not jp_chars.search(value), f"{name}:{key} contains Japanese characters"


def test_resolve_user_lang_respects_unsaved_users() -> None:
    user = SimpleNamespace(id=987654321, language_code="en")
    message = SimpleNamespace(text="/start", from_user=user)
    lang, persisted = main.resolve_user_lang(message)

    assert lang == "en"
    assert persisted is False
    assert get_user_lang(user.id) is None
