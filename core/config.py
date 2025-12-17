import os

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "hasegawaarisa1@gmail.com")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment or .env")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set in environment or .env")
