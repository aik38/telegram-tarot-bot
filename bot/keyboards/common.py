from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

MENU_HOME_TEXT = "🏠 メニューへ戻る"


def nav_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=MENU_HOME_TEXT, callback_data="nav:menu")]]
    )


def menu_only_kb() -> InlineKeyboardMarkup:
    return nav_kb()


def base_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎩占い"), KeyboardButton(text="💬相談")],
            [KeyboardButton(text="🛒チャージ"), KeyboardButton(text="📊ステータス")],
        ],
        is_persistent=True,
        resize_keyboard=True,
    )
