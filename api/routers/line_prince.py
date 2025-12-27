from fastapi import APIRouter, status

router = APIRouter()


@router.post("/webhooks/line", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def handle_line_webhook() -> dict[str, str]:
    return {"detail": "Not implemented"}
