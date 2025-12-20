from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.texts.i18n import normalize_lang, t


def nav_kb(lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang_code, "MENU_HOME_TEXT"), callback_data="nav:menu")]
        ]
    )


def menu_only_kb() -> InlineKeyboardMarkup:
    return nav_kb()


def base_menu_kb(lang: str | None = "ja") -> ReplyKeyboardMarkup:
    lang_code = normalize_lang(lang)
    labels = (
        (
            t(lang_code, "MENU_TAROT_LABEL"),
            t(lang_code, "MENU_CHAT_LABEL"),
        ),
        (
            t(lang_code, "MENU_STORE_LABEL"),
            t(lang_code, "MENU_STATUS_LABEL"),
            t(lang_code, "MENU_LANGUAGE_LABEL"),
        ),
    )
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=labels[0][0]), KeyboardButton(text=labels[0][1])],
            [
                KeyboardButton(text=labels[1][0]),
                KeyboardButton(text=labels[1][1]),
                KeyboardButton(text=labels[1][2]),
            ],
        ],
        is_persistent=True,
        resize_keyboard=True,
    )
