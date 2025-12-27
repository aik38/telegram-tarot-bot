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

router = APIRouter()


class LineMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    id: str
    type: str
    text: str | None = None


class LineSource(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: str | None = None
    user_id: str | None = Field(default=None, alias="userId")


class LineEvent(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    type: str
    reply_token: str | None = Field(default=None, alias="replyToken")
    message: LineMessage | None = None
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
    raw = os.getenv("ADMIN_LINE_USER_IDS", "")
    return {user_id.strip() for user_id in raw.split(",") if user_id.strip()}


async def _handle_message_event(
    event: LineEvent,
    db: CommonBackendDB,
    line_client: LineReplyClient,
    admin_user_ids: set[str],
) -> None:
    if not event.reply_token or not event.source.user_id or not event.message:
        return

    account_id, _ = db.resolve_identity("line", event.source.user_id)

    is_admin = event.source.user_id in admin_user_ids
    request_id = f"line:{event.source.user_id}:{event.message.id}"

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

    if allowed:
        reply_text = event.message.text or ""
    else:
        reply_text = "今月の無料枠が終了しました。追加の利用をご希望の場合は、決済ページからプランをご検討ください（準備中）。"

    await line_client.reply_text(event.reply_token, reply_text)


@router.post("/webhooks/line")
async def handle_line_webhook(
    request: Request,
    x_line_signature: str | None = Header(default=None),
    db: CommonBackendDB = Depends(common_backend.get_db),
    line_client: LineReplyClient = Depends(get_line_client),
) -> dict[str, str]:
    channel_secret = os.getenv("LINE_CHANNEL_SECRET")
    if not channel_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LINE_CHANNEL_SECRET is not configured",
        )

    if not x_line_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing X-Line-Signature header",
        )

    body = await request.body()
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
        if event.type == "message" and event.message and event.message.type == "text"
    )

    for event in message_events:
        await _handle_message_event(event, db, line_client, admin_user_ids)

    return {"status": "ok"}
