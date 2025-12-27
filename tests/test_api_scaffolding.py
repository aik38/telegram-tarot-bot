from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def assert_not_implemented(path: str) -> None:
    response = client.post(path)
    assert response.status_code == 501
    assert response.json() == {"detail": "Not implemented"}


def test_line_prince_webhook_placeholder() -> None:
    assert_not_implemented("/webhooks/line")


def test_stripe_webhook_placeholder() -> None:
    assert_not_implemented("/webhooks/stripe")


def test_telegram_prince_webhook_placeholder() -> None:
    assert_not_implemented("/webhooks/telegram/prince")
