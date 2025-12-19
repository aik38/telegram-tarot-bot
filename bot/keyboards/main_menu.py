from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.common import menu_only_kb


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔮 占う", callback_data="menu:read")],
            [InlineKeyboardButton(text="❓ 使い方", callback_data="menu:help")],
            [InlineKeyboardButton(text="📜 規約", callback_data="menu:terms")],
            [InlineKeyboardButton(text="🛟 サポート", callback_data="menu:support")],
        ]
    )


def spread_select_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1枚", callback_data="spread:one"),
                InlineKeyboardButton(text="3枚", callback_data="spread:three"),
            ],
            [InlineKeyboardButton(text="🏠 メニュー", callback_data="nav:menu")],
        ]
    )


__all__ = [
    "main_menu_kb",
    "spread_select_kb",
    "menu_only_kb",
]
