import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from bot.texts.i18n import normalize_lang, t
from core.db import get_user_lang


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, min_interval_sec: float = 1.2, apply_to_callbacks: bool = True) -> None:
        super().__init__()
        self.min_interval_sec = min_interval_sec
        self.apply_to_callbacks = apply_to_callbacks
        self._last_seen: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery | Message, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery | Message,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, CallbackQuery) and not self.apply_to_callbacks:
            return await handler(event, data)

        user_id = self._get_user_id(event)
        now = time.monotonic()
        if user_id is not None:
            last = self._last_seen.get(user_id)
            if last is not None and (now - last) < self.min_interval_sec:
                await self._handle_throttled(event)
                return
            self._last_seen[user_id] = now

        return await handler(event, data)

    def _get_user_id(self, event: CallbackQuery | Message) -> int | None:
        if isinstance(event, CallbackQuery):
            return event.from_user.id if event.from_user else None
        return event.from_user.id if event.from_user else None

    async def _handle_throttled(self, event: CallbackQuery | Message) -> None:
        lang = self._resolve_lang(event)
        text = t(lang, "THROTTLE_TEXT")
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(text, show_alert=False)
            else:
                await event.answer(text)
        except Exception:
            # Avoid raising from middleware
            return

    def _resolve_lang(self, event: CallbackQuery | Message) -> str:
        user_id = self._get_user_id(event)
        saved_lang = get_user_lang(user_id) if user_id is not None else None
        if saved_lang:
            return saved_lang
        language_code = getattr(getattr(event, "from_user", None), "language_code", None)
        return normalize_lang(language_code)
