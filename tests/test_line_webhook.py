from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.routers import common_backend, line_webhook
from api.routers.line_webhook import compute_signature
from api.services.line_prince import PrinceChatService


class StubDB:
    def __init__(self, consume_allowed: bool = True) -> None:
        self.consume_allowed = consume_allowed
        self.resolve_calls: list[tuple[str, str]] = []
        self.consume_calls: list[dict[str, Any]] = []

    def resolve_identity(self, provider: str, provider_user_id: str) -> tuple[int, int]:
        self.resolve_calls.append((provider, provider_user_id))
        return 100, 200

    def consume_entitlement(
        self, account_id: int, feature: str, units: int, request_id: str
    ) -> tuple[bool, int]:
        self.consume_calls.append(
            {
                "account_id": account_id,
                "feature": feature,
                "units": units,
                "request_id": request_id,
            }
        )
        return self.consume_allowed, 0


class StubLineClient:
    def __init__(self) -> None:
        self.replies: list[tuple[str, str]] = []

    async def reply_text(self, reply_token: str, text: str) -> None:
        self.replies.append((reply_token, text))


class StubPrinceChatService(PrinceChatService):
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def generate_reply(self, user_message: str) -> str:
        self.calls.append(user_message)
        return f"prince:{user_message}"


@pytest.fixture()
def line_test_app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "token")
    monkeypatch.delenv("LINE_ADMIN_USER_IDS", raising=False)
    monkeypatch.delenv("ADMIN_LINE_USER_IDS", raising=False)

    stub_db = StubDB()
    stub_client = StubLineClient()
    stub_prince = StubPrinceChatService()

    app.dependency_overrides[common_backend.get_db] = lambda: stub_db
    app.dependency_overrides[line_webhook.get_line_client] = lambda: stub_client
    app.dependency_overrides[line_webhook.get_prince_chat_service] = lambda: stub_prince

    with TestClient(app) as test_client:
        yield test_client, stub_db, stub_client, stub_prince

    app.dependency_overrides.pop(common_backend.get_db, None)
    app.dependency_overrides.pop(line_webhook.get_line_client, None)
    app.dependency_overrides.pop(line_webhook.get_prince_chat_service, None)


def make_signed_body(secret: str, payload: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    signature = compute_signature(secret, body)
    headers = {
        "content-type": "application/json",
        "x-line-signature": signature,
    }
    return body, headers


def test_whoami_returns_user_id(line_test_app) -> None:
    client, db, stub_client, _ = line_test_app
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-1",
                "message": {"id": "m-1", "type": "text", "text": "/whoami"},
                "source": {"type": "user", "userId": "user-1"},
            }
        ]
    }
    body, headers = make_signed_body("secret", payload)

    response = client.post("/line/webhook", content=body, headers=headers)

    assert response.status_code == 200
    assert db.consume_calls == []
    assert stub_client.replies == [("reply-1", "LINE userId: user-1")]


def test_admin_feature_available_only_for_admin(monkeypatch: pytest.MonkeyPatch, line_test_app) -> None:
    client, db, stub_client, _ = line_test_app
    monkeypatch.setenv("LINE_ADMIN_USER_IDS", "admin-user")

    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-2",
                "message": {"id": "m-2", "type": "text", "text": "今日の星"},
                "source": {"type": "user", "userId": "admin-user"},
            }
        ]
    }
    body, headers = make_signed_body("secret", payload)

    response = client.post("/line/webhook", content=body, headers=headers)

    assert response.status_code == 200
    assert db.consume_calls == []
    assert "星のきらめき" in stub_client.replies[0][1]


def test_general_users_get_coming_soon_message(line_test_app) -> None:
    client, db, stub_client, _ = line_test_app
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-3",
                "message": {"id": "m-3", "type": "text", "text": "ミニ占い"},
                "source": {"type": "user", "userId": "user-3"},
            }
        ]
    }
    body, headers = make_signed_body("secret", payload)

    response = client.post("/line/webhook", content=body, headers=headers)

    assert response.status_code == 200
    assert db.consume_calls == []
    assert stub_client.replies == [("reply-3", "近日公開。今は「話す」だけ先行公開中です。")]


def test_entitlement_blocks_and_prince_chat_called(line_test_app) -> None:
    client, db, stub_client, stub_prince = line_test_app
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-4",
                "message": {"id": "m-4", "type": "text", "text": "こんにちは"},
                "source": {"type": "user", "userId": "user-4"},
            }
        ]
    }
    body, headers = make_signed_body("secret", payload)

    response = client.post("/line/webhook", content=body, headers=headers)

    assert response.status_code == 200
    assert db.consume_calls == [
        {
            "account_id": 100,
            "feature": "line.text",
            "units": 1,
            "request_id": "line:user-4:m-4",
        }
    ]
    assert stub_prince.calls == ["こんにちは"]
    assert stub_client.replies == [("reply-4", "prince:こんにちは")]


def test_invalid_signature_returns_unauthorized(line_test_app) -> None:
    client, db, stub_client, stub_prince = line_test_app
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-5",
                "message": {"id": "m-5", "type": "text", "text": "hi"},
                "source": {"type": "user", "userId": "user-5"},
            }
        ]
    }
    body = json.dumps(payload).encode()
    headers = {
        "content-type": "application/json",
        "x-line-signature": "invalid",
    }

    response = client.post("/line/webhook", content=body, headers=headers)

    assert response.status_code == 401
    assert db.consume_calls == []
    assert stub_prince.calls == []
    assert stub_client.replies == []


def test_denied_entitlement_returns_limit_message(line_test_app) -> None:
    client, db, stub_client, _ = line_test_app
    db.consume_allowed = False
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "reply-6",
                "message": {"id": "m-6", "type": "text", "text": "please"},
                "source": {"type": "user", "userId": "user-6"},
            }
        ]
    }
    body, headers = make_signed_body("secret", payload)

    response = client.post("/line/webhook", content=body, headers=headers)

    assert response.status_code == 200
    assert stub_client.replies == [
        (
            "reply-6",
            "今月の無料枠が終了しました。追加の利用をご希望の場合は、決済ページからプランをご検討ください（準備中）。",
        )
    ]
