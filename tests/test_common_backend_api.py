from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.db.common_backend import CommonBackendDB
from api.main import app
from api.routers import common_backend


@pytest.fixture()
def client(tmp_path) -> TestClient:
    db_path = tmp_path / "common_backend.db"
    test_db = CommonBackendDB(db_path)
    app.dependency_overrides[common_backend.get_db] = lambda: test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(common_backend.get_db, None)


def resolve_account(client: TestClient, provider_user_id: str) -> dict[str, int]:
    response = client.post(
        "/api/v1/identities/resolve",
        json={"provider": "telegram", "provider_user_id": provider_user_id},
    )
    assert response.status_code == 200
    return response.json()


def test_resolve_creates_account_and_identity(client: TestClient) -> None:
    first = resolve_account(client, "user-1")
    second = resolve_account(client, "user-1")

    assert first["account_id"] == second["account_id"]
    assert first["identity_id"] == second["identity_id"]


def test_check_returns_default_entitlement(client: TestClient) -> None:
    resolved = resolve_account(client, "user-2")
    response = client.post(
        "/api/v1/entitlements/check", json={"account_id": resolved["account_id"]}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["plan_key"] == "free"
    assert data["credits_remaining"] == 3
    assert data["allowed"] is True
    assert data["period_end"]


def test_consume_decrements_and_is_idempotent(client: TestClient) -> None:
    resolved = resolve_account(client, "user-3")
    account_id = resolved["account_id"]

    first = client.post(
        "/api/v1/entitlements/consume",
        json={
            "account_id": account_id,
            "feature": "tarot",
            "units": 1,
            "request_id": "req-1",
        },
    )
    assert first.status_code == 200
    assert first.json() == {"allowed": True, "credits_remaining": 2}

    duplicate = client.post(
        "/api/v1/entitlements/consume",
        json={
            "account_id": account_id,
            "feature": "tarot",
            "units": 1,
            "request_id": "req-1",
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json() == {"allowed": True, "credits_remaining": 2}

    second = client.post(
        "/api/v1/entitlements/consume",
        json={
            "account_id": account_id,
            "feature": "tarot",
            "units": 2,
            "request_id": "req-2",
        },
    )
    assert second.status_code == 200
    assert second.json() == {"allowed": True, "credits_remaining": 0}

    denied = client.post(
        "/api/v1/entitlements/consume",
        json={
            "account_id": account_id,
            "feature": "tarot",
            "units": 1,
            "request_id": "req-3",
        },
    )
    assert denied.status_code == 200
    assert denied.json() == {"allowed": False, "credits_remaining": 0}
