import os
from pathlib import Path
from typing import Set

from dotenv import load_dotenv

dotenv_path = Path(os.getenv("DOTENV_FILE", Path(__file__).resolve().parents[1] / ".env"))
load_dotenv(dotenv_path, override=False)


def _parse_admin_ids(raw: str) -> Set[int]:
    values: set[int] = set()
    for value in (raw or "").split(","):
        candidate = value.strip()
        if not candidate:
            continue
        try:
            values.add(int(candidate))
        except ValueError:
            continue
    return values


def _parse_float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "hasegawaarisa1@gmail.com")
ADMIN_USER_IDS = _parse_admin_ids(os.getenv("ADMIN_USER_IDS", ""))
THROTTLE_MESSAGE_INTERVAL_SEC = _parse_float_env("THROTTLE_MESSAGE_INTERVAL_SEC", 1.2)
THROTTLE_CALLBACK_INTERVAL_SEC = _parse_float_env("THROTTLE_CALLBACK_INTERVAL_SEC", 0.8)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment or .env")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment or .env")
