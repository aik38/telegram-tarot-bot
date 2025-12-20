from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove

from bot.keyboards.common import base_menu_kb


def ensure_quick_menu(
    reply_markup: ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove | None = None,
) -> ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove:
    """
    Always return a reply markup that keeps the quick menu visible.

    If a reply markup is already provided, it is returned unchanged to avoid altering
    other inline keyboards. Otherwise the persistent base menu is attached.
    """
    return reply_markup if reply_markup is not None else base_menu_kb()
