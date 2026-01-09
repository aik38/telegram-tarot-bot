import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI

from api.db import apply_migrations

from api.routers import common_backend, line_webhook, stripe, tg_prince

logger = logging.getLogger(__name__)

dotenv_path = Path(
    os.getenv("DOTENV_FILE", Path(__file__).resolve().parents[1] / ".env")
)
load_dotenv(dotenv_path, override=False)

app = FastAPI()


def _log_env_status() -> None:
    logger.info(
        "Environment flags -> OPENAI_API_KEY set: %s, LINE_CHANNEL_ACCESS_TOKEN set: %s, LINE_CHANNEL_SECRET set: %s",
        bool(os.getenv("OPENAI_API_KEY")),
        bool(os.getenv("LINE_CHANNEL_ACCESS_TOKEN")),
        bool(os.getenv("LINE_CHANNEL_SECRET")),
    )


@app.get("/api/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
def run_migrations() -> None:
    _log_env_status()
    apply_migrations()


app.include_router(line_webhook.router)
app.include_router(stripe.router)
app.include_router(tg_prince.router)
app.include_router(common_backend.router)
