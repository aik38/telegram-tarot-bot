import asyncio
import os

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123456:TESTTOKEN")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")

from bot.main import IN_FLIGHT_USERS, _acquire_inflight


class _DummyMessage:
    def __init__(self, user_id: int) -> None:
        self.from_user = type("User", (), {"id": user_id})
        self.answers: list[str] = []

    async def answer(self, text: str, show_alert: bool | None = None) -> None:  # noqa: ARG002
        self.answers.append(text)


def test_requests_from_same_user_are_queued_with_notice() -> None:
    async def _run() -> None:
        first = _DummyMessage(user_id=42)
        release_first = await _acquire_inflight(42, first, busy_message="wait")

        second = _DummyMessage(user_id=42)
        second_task = asyncio.create_task(
            _acquire_inflight(42, second, busy_message="wait")
        )

        await asyncio.sleep(0.01)
        assert second.answers == ["wait"]
        assert not second_task.done()
        assert 42 in IN_FLIGHT_USERS

        release_first()
        release_second = await second_task
        assert 42 in IN_FLIGHT_USERS

        release_second()
        assert 42 not in IN_FLIGHT_USERS
        assert first.answers == []

    asyncio.run(_run())
