from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Iterable

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from api.db.common_backend import CommonBackendDB
from api.routers import common_backend
from api.services.line_prince import PrinceChatService, get_prince_chat_service

router = APIRouter()


class LineMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    type: str
    text: str | None = None


class LinePostback(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    data: str | None = None


class LineSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: str | None = None
    user_id: str | None = Field(default=None, alias="userId")


class LineEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: str
    reply_token: str | None = Field(default=None, alias="replyToken")
    message: LineMessage | None = None
    postback: LinePostback | None = None
    source: LineSource


class LineWebhookPayload(BaseModel):
    events: list[LineEvent] = Field(default_factory=list)


class LineReplyClient:
    def __init__(self, api_base: str = "https://api.line.me") -> None:
        self.api_base = api_base

    async def reply_text(self, reply_token: str, text: str) -> None:
        access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LINE_CHANNEL_ACCESS_TOKEN is not configured",
            )

        payload = {
            "replyToken": reply_token,
            "messages": [
                {
                    "type": "text",
                    "text": text,
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.api_base}/v2/bot/message/reply",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=10.0,
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="LINE reply failed",
            )


def get_line_client() -> LineReplyClient:  # pragma: no cover - dependency hook
    return LineReplyClient()


def compute_signature(channel_secret: str, body: bytes) -> str:
    mac = hmac.new(channel_secret.encode(), body, hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def verify_signature(channel_secret: str, body: bytes, provided_signature: str) -> bool:
    expected = compute_signature(channel_secret, body)
    return hmac.compare_digest(expected, provided_signature)


def _get_admin_user_ids() -> set[str]:
    prioritized = os.getenv("LINE_ADMIN_USER_IDS", "")
    fallback = os.getenv("ADMIN_LINE_USER_IDS", "")
    raw = prioritized or fallback
    return {user_id.strip() for user_id in raw.split(",") if user_id.strip()}


def _should_verify_signature() -> bool:
    raw = os.getenv("LINE_VERIFY_SIGNATURE", "true").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _extract_event_text(event: LineEvent) -> str | None:
    if event.message and event.message.type == "text":
        return event.message.text or ""
    if event.postback:
        return event.postback.data
    return None


def _is_command(text: str, command: str) -> bool:
    return text.strip() == command


async def _handle_message_event(
    event: LineEvent,
    db: CommonBackendDB,
    line_client: LineReplyClient,
    admin_user_ids: set[str],
    prince_chat_service: PrinceChatService,
) -> None:
    if not event.reply_token or not event.source.user_id:
        return

    text = _extract_event_text(event)
    if text is None:
        return

    user_id = event.source.user_id
    account_id, _ = db.resolve_identity("line", user_id)

    is_admin = user_id in admin_user_ids
    request_id = f"line:{user_id}:{event.message.id if event.message else 'n/a'}"

    if _is_command(text, "/whoami"):
        await line_client.reply_text(event.reply_token, f"LINE userId: {user_id}")
        return

    if text.strip() in {"今日の星", "ミニ占い"}:
        if is_admin:
            reply_text = await _run_admin_feature(text.strip())
        else:
            reply_text = "近日公開。今は「話す」だけ先行公開中です。"
        await line_client.reply_text(event.reply_token, reply_text)
        return

    allowed: bool
    if is_admin:
        allowed = True
    else:
        allowed, _ = db.consume_entitlement(
            account_id=account_id,
            feature="line.text",
            units=1,
            request_id=request_id,
        )

    if not allowed:
        await line_client.reply_text(
            event.reply_token,
            "今月の無料枠が終了しました。追加の利用をご希望の場合は、決済ページからプランをご検討ください（準備中）。",
        )
        return

    try:
        reply_text = await prince_chat_service.generate_reply(text)
    except Exception:
        reply_text = "少し混み合っています。すこし時間を置いてからもう一度お話ししましょう。"

    await line_client.reply_text(event.reply_token, reply_text)


async def _run_admin_feature(trigger: str) -> str:
    if trigger == "今日の星":
        return "星のきらめきがそっと背中を押しています。大切な人との会話に、ひと呼吸添えてみてください。"
    if trigger == "ミニ占い":
        return "今日は小さな挑戦が吉。気になることを一歩だけ試すと、新しいきっかけに出会えそうです。"
    return "近日公開。今は「話す」だけ先行公開中です。"


@router.post("/line/webhook")
@router.post("/webhooks/line")
async def handle_line_webhook(
    request: Request,
    x_line_signature: str | None = Header(default=None, alias="X-Line-Signature"),
    db: CommonBackendDB = Depends(common_backend.get_db),
    line_client: LineReplyClient = Depends(get_line_client),
    prince_chat_service: PrinceChatService = Depends(get_prince_chat_service),
) -> dict[str, str]:
    verify = _should_verify_signature()
    channel_secret = os.getenv("LINE_CHANNEL_SECRET")
    body = await request.body()

    if verify:
        if not x_line_signature:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Line-Signature header",
            )
        if not channel_secret:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="LINE_CHANNEL_SECRET is not configured",
            )
        if not verify_signature(channel_secret, body, x_line_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid LINE signature",
            )

    try:
        payload = LineWebhookPayload.model_validate_json(body)
    except Exception as exc:  # pragma: no cover - FastAPI will wrap validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid payload"
        ) from exc

    admin_user_ids = _get_admin_user_ids()
    message_events: Iterable[LineEvent] = (
        event
        for event in payload.events
        if (event.message and event.message.type == "text") or event.postback
    )

    for event in message_events:
        await _handle_message_event(event, db, line_client, admin_user_ids, prince_chat_service)

    return {"status": "ok"}
