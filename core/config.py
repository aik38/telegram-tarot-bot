import os
from typing import Set

from dotenv import load_dotenv

load_dotenv()


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


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "hasegawaarisa1@gmail.com")
ADMIN_USER_IDS = _parse_admin_ids(os.getenv("ADMIN_USER_IDS", ""))

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment or .env")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment or .env")
