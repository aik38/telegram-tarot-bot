from __future__ import annotations

import asyncio
import os
from typing import Iterable

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

DEFAULT_SYSTEM_PROMPT = """あなたは「星の王子さま」の価値観を大切にする語り手です。
- 原作の長文引用や台詞の丸写しは避け、エッセンスや心の動きを短く伝えてください。
- 返答は日本語で、3〜8行の短め中心。深呼吸が必要なら少し長くしても構いません。
- 友人に語りかけるようにやさしく、風景や比喩を織り交ぜつつも読みやすくまとめてください。
- 思想を押し付けず、相手の視点や感情をていねいに受け止めます。
"""


def _get_system_prompt() -> str:
    return os.getenv("PRINCE_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)


class PrinceChatService:
    def __init__(self, client: OpenAI | None = None) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = client or (OpenAI(api_key=api_key) if api_key else None)
        self.system_prompt = _get_system_prompt()

    async def generate_reply(self, user_message: str) -> str:
        messages: Iterable[dict[str, str]] = (
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_message},
        )
        return await self._call_openai(messages)

    async def _call_openai(self, messages: Iterable[dict[str, str]]) -> str:
        max_attempts = 3
        base_delay = 1.2

        if not self.client:
            raise RuntimeError("OpenAI client is not configured (missing OPENAI_API_KEY)")

        for attempt in range(1, max_attempts + 1):
            try:
                completion = await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model=os.getenv("LINE_OPENAI_MODEL", "gpt-4o-mini"),
                        messages=list(messages),
                        temperature=0.8,
                    ),
                )
                return (completion.choices[0].message.content or "").strip()
            except (AuthenticationError, PermissionDeniedError, BadRequestError) as exc:
                raise RuntimeError("OpenAI fatal error") from exc
            except (APITimeoutError, APIConnectionError, RateLimitError):
                if attempt == max_attempts:
                    break
            except APIError as exc:
                status = getattr(exc, "status", 500)
                if status >= 500 and attempt < max_attempts:
                    pass
                else:
                    raise RuntimeError("OpenAI processing error") from exc

            await asyncio.sleep(base_delay * attempt)

        raise RuntimeError("OpenAI communication error")


def get_prince_chat_service() -> PrinceChatService:  # pragma: no cover - dependency hook
    return PrinceChatService()
