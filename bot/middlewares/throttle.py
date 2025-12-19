import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message

from bot.texts.ja import THROTTLE_TEXT


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, min_interval_sec: float = 1.2) -> None:
        super().__init__()
        self.min_interval_sec = min_interval_sec
        self._last_seen: Dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[CallbackQuery | Message, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery | Message,
        data: Dict[str, Any],
    ) -> Any:
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
        try:
            if isinstance(event, CallbackQuery):
                await event.answer(THROTTLE_TEXT, show_alert=False)
            else:
                await event.answer(THROTTLE_TEXT)
        except Exception:
            # Avoid raising from middleware
            return
