from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.texts.i18n import normalize_lang

MENU_HOME_TEXT = "🏠 メニューへ戻る"
MENU_LABELS: dict[str, tuple[tuple[str, str], tuple[str, str]]] = {
    "ja": (("🎩占い", "💬相談"), ("🛒チャージ", "📊ステータス")),
    "en": (("🎩 Tarot", "💬 Chat"), ("🛒 Store", "📊 Status")),
    "pt": (("🎩 Tarot", "💬 Conversa"), ("🛒 Loja", "📊 Status")),
}


def nav_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=MENU_HOME_TEXT, callback_data="nav:menu")]]
    )


def menu_only_kb() -> InlineKeyboardMarkup:
    return nav_kb()


def base_menu_kb(lang: str | None = "ja") -> ReplyKeyboardMarkup:
    lang_code = normalize_lang(lang)
    labels = MENU_LABELS.get(lang_code, MENU_LABELS["ja"])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels[0][0]), KeyboardButton(text=labels[0][1])],
            [KeyboardButton(text=labels[1][0]), KeyboardButton(text=labels[1][1])],
        ],
        is_persistent=True,
        resize_keyboard=True,
    )
