from fastapi import APIRouter, status

router = APIRouter()


@router.post("/webhooks/telegram/prince", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def handle_telegram_prince_webhook() -> dict[str, str]:
    return {"detail": "Not implemented"}
