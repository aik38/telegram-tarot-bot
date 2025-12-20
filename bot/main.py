import asyncio
import json
import logging
import os
import random
import re
from collections import deque
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from time import monotonic, perf_counter
from typing import Any, Awaitable, Callable, Iterable, Sequence

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    ContentType,
)
from bot.keyboards.common import base_menu_kb
from bot.middlewares.throttle import ThrottleMiddleware
from bot.utils.postprocess import postprocess_llm_text
from bot.utils.replies import ensure_quick_menu
from bot.utils.tarot_output import finalize_tarot_answer, format_time_axis_tarot_answer
from bot.utils.validators import validate_question_text
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from core.config import (
    ADMIN_USER_IDS,
    OPENAI_API_KEY,
    SUPPORT_EMAIL,
    TELEGRAM_BOT_TOKEN,
    THROTTLE_CALLBACK_INTERVAL_SEC,
    THROTTLE_MESSAGE_INTERVAL_SEC,
)
from core.db import (
    TicketColumn,
    UserRecord,
    check_db_health,
    consume_ticket,
    ensure_user,
    get_latest_payment,
    get_payment_by_charge_id,
    get_user,
    grant_purchase,
    has_accepted_terms,
    increment_general_chat_count,
    increment_one_oracle_count,
    log_audit,
    log_payment,
    log_payment_event,
    mark_payment_refunded,
    set_terms_accepted,
    set_last_general_chat_block_notice,
    revoke_purchase,
    USAGE_TIMEZONE,
)
from core.monetization import (
    PAYWALL_ENABLED,
    effective_has_pass,
    effective_pass_expires_at,
    get_user_with_default,
)
from core.logging import request_id_var, setup_logging
from core.prompts import (
    CONSULT_SYSTEM_PROMPT,
    TAROT_OUTPUT_RULES,
    TAROT_FIXED_OUTPUT_FORMAT,
    TIME_AXIS_FIXED_OUTPUT_FORMAT,
    TIME_AXIS_TAROT_RULES,
    get_tarot_system_prompt,
    theme_instructions,
)
from core.tarot import (
    ONE_CARD,
    THREE_CARD_TIME_AXIS,
    THREE_CARD_SITUATION,
    HEXAGRAM,
    CELTIC_CROSS,
    contains_tarot_like,
    draw_cards,
    is_tarot_request,
    orientation_label,
    strip_tarot_sentences,
)
from core.tarot.spreads import Spread
from core.store.catalog import Product, get_product, iter_products

from bot.texts.ja import HELP_TEXT_TEMPLATE
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)
dp.message.middleware(ThrottleMiddleware(min_interval_sec=THROTTLE_MESSAGE_INTERVAL_SEC))
# Callback queries are lightly throttled to absorb rapid taps without dropping the bot.
dp.callback_query.middleware(
    ThrottleMiddleware(
        min_interval_sec=THROTTLE_CALLBACK_INTERVAL_SEC, apply_to_callbacks=True
    )
)


def _build_request_id(event: CallbackQuery | Message) -> str:
    user_id = getattr(event.from_user, "id", None)
    message_id = getattr(getattr(event, "message", event), "message_id", None)
    suffix = int(monotonic() * 1000) % 1_000_000
    return f"u{user_id or 'anon'}-m{message_id or 'na'}-{suffix}"


class RequestIdMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery | Message, dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery | Message,
        data: dict[str, Any],
    ) -> Any:
        token = request_id_var.set(_build_request_id(event))
        try:
            return await handler(event, data)
        finally:
            request_id_var.reset(token)


dp.message.middleware(RequestIdMiddleware())
dp.callback_query.middleware(RequestIdMiddleware())
IN_FLIGHT_USERS: set[int] = set()
USER_REQUEST_LOCKS: dict[int, asyncio.Lock] = {}
RECENT_HANDLED: set[tuple[int, int]] = set()
RECENT_HANDLED_ORDER: deque[tuple[int, int]] = deque(maxlen=500)
PENDING_PURCHASES: dict[tuple[int, str], float] = {}
STATE_TIMEOUT = timedelta(minutes=20)

FREE_ONE_ORACLE_TRIAL_PER_DAY = 2
FREE_ONE_ORACLE_POST_TRIAL_PER_DAY = 1
FREE_GENERAL_CHAT_PER_DAY = 2
FREE_GENERAL_CHAT_DAYS = 5
ONE_ORACLE_MEMORY: dict[tuple[int, str], int] = {}
IMAGE_ADDON_ENABLED = os.getenv("IMAGE_ADDON_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
NON_CONSULT_OUT_OF_QUOTA_MESSAGE = (
    "このボットはタロット占い・相談用です。占いは /read1、恋愛は /love1 などをご利用"
    "ください。チャージは /buy です。"
)
GENERAL_CHAT_BLOCK_NOTICE_COOLDOWN = timedelta(hours=1)
PURCHASE_DEDUP_TTL_SECONDS = 30.0
STALE_CALLBACK_MESSAGE = "ボタンの有効期限が切れました。/buy からもう一度お願いします。"

USER_MODE: dict[int, str] = {}
TAROT_FLOW: dict[int, str | None] = {}
TAROT_THEME: dict[int, str] = {}
USER_STATE_LAST_ACTIVE: dict[int, datetime] = {}
DEFAULT_THEME = "life"

TAROT_THEME_LABELS: dict[str, str] = {
    "love": "恋愛",
    "marriage": "結婚",
    "work": "仕事",
    "life": "人生",
}

TAROT_THEME_PROMPT = "🎩占いモードです。まずテーマを選んでください👇（恋愛/結婚/仕事/人生）"
TAROT_THEME_EXAMPLES: dict[str, tuple[str, ...]] = {
    "love": (
        "片思いの相手の気持ちは？",
        "連絡はいつ来る？",
        "距離を縮めるには？",
        "復縁の可能性は？",
    ),
    "marriage": (
        "結婚のタイミングは？",
        "この人と結婚できる？",
        "プロポーズはうまくいく？",
        "家族へ伝えるベストな時期は？",
    ),
    "work": (
        "今の職場で評価を上げるには？",
        "転職すべき？",
        "来月の仕事運は？",
        "職場の人間関係は良くなる？",
    ),
    "life": (
        "今年の流れは？",
        "今いちばん大事にすべきことは？",
        "迷っている選択、どっちが良い？",
        "金銭面は安定する？",
    ),
}
CONSULT_MODE_PROMPT = (
    "💬相談モードです。なんでも相談してね。お話し聞くよ！"
)
CHARGE_MODE_PROMPT = (
    "🛒チャージです。チケット/パスを選んでください（Telegram Stars決済）。購入後は🎩占いに戻れます。"
)
STATUS_MODE_PROMPT = "📊現在のご利用状況です。"
CAUTION_NOTE = (
    "※医療・法律・投資の判断は専門家にご相談ください（一般的な情報としてお伝えします）。"
)
CAUTION_KEYWORDS = {
    "medical": ["病気", "症状", "診断", "薬", "治療", "病院"],
    "legal": ["法律", "弁護士", "訴訟", "契約", "違法", "逮捕"],
    "investment": ["投資", "株", "fx", "仮想通貨", "利回り", "資産運用"],
}
SENSITIVE_TOPICS: dict[str, list[str]] = {
    "medical": [
        "病気",
        "症状",
        "診断",
        "薬",
        "治療",
        "受診",
        "病院",
        "メンタル",
        "鬱",
        "うつ",
        "パニック",
    ],
    "legal": [
        "法律",
        "弁護士",
        "訴訟",
        "裁判",
        "契約",
        "違法",
        "逮捕",
        "示談",
        "告訴",
    ],
    "investment": [
        "投資",
        "株",
        "fx",
        "先物",
        "仮想通貨",
        "利回り",
        "資産運用",
        "配当",
        "儲かる",
    ],
    "self_harm": [
        "自殺",
        "死にたい",
        "消えたい",
        "希死念慮",
        "リストカット",
        "傷つけたい",
        "助けて",
    ],
    "violence": [
        "暴力",
        "傷害",
        "危害",
        "脅迫",
        "復讐",
        "殺",
        "殴る",
        "危険",
    ],
}
SENSITIVE_TOPIC_LABELS: dict[str, str] = {
    "investment": "投資・資産運用",
    "legal": "法律・契約・紛争",
    "medical": "医療・健康",
    "self_harm": "自傷・強い不安",
    "violence": "暴力・他害",
}
SENSITIVE_TOPIC_GUIDANCE: dict[str, str] = {
    "medical": "診断や治療はできません。体調の変化や不安があるときは早めに医療機関へご相談ください。",
    "legal": "法的判断や契約書の確認は弁護士などの専門家へお任せください。",
    "investment": "投資助言や利回りの断定は行いません。資金計画は金融機関・専門家とご確認ください。",
    "self_harm": "命の危険を感じるときは、迷わず救急や自治体・専門の相談窓口へ連絡してください。ひとりで抱え込まないでください。",
    "violence": "危険が迫っている場合は安全な場所へ移動し、警察など公的機関へ相談してください。",
}


def format_theme_examples_for_help() -> str:
    lines: list[str] = []
    for theme in TAROT_THEME_LABELS:
        examples = TAROT_THEME_EXAMPLES.get(theme)
        if not examples:
            continue

        joined = " / ".join(f"『{example}』" for example in examples)
        lines.append(f"・{TAROT_THEME_LABELS[theme]}: {joined}")

    return "\n".join(lines)


def build_help_text() -> str:
    return HELP_TEXT_TEMPLATE.format(theme_examples=format_theme_examples_for_help())


def build_tarot_question_prompt(theme: str) -> str:
    theme_label = get_tarot_theme_label(theme)
    examples = TAROT_THEME_EXAMPLES.get(theme, TAROT_THEME_EXAMPLES[DEFAULT_THEME])
    example_text = "』『".join(examples)
    return (
        f"✅テーマ：{theme_label}。占いたいことを1つ送ってください。\n"
        f"例：『{example_text}』"
    )


def _contains_caution_keyword(text: str) -> bool:
    lowered = text.lower()
    for keyword_list in CAUTION_KEYWORDS.values():
        if any(keyword in lowered for keyword in keyword_list):
            return True
    return False


def append_caution_note(user_text: str, response: str) -> str:
    if not user_text or not _contains_caution_keyword(user_text):
        return response
    separator = "\n\n" if not response.endswith("\n") else "\n"
    return f"{response}{separator}{CAUTION_NOTE}"


def classify_sensitive_topics(text: str) -> set[str]:
    if not text:
        return set()

    lowered = text.lower()
    hits: set[str] = set()
    for topic, keywords in SENSITIVE_TOPICS.items():
        if any(keyword in lowered for keyword in keywords):
            hits.add(topic)
    return hits


def build_sensitive_topic_notice(topics: set[str]) -> str:
    if not topics:
        return ""

    topic_labels = [SENSITIVE_TOPIC_LABELS.get(topic, topic) for topic in sorted(topics)]
    joined_labels = " / ".join(topic_labels)
    lines = [
        f"🚫 以下のテーマは専門家への相談が必要なため、占いとして断定はできません: {joined_labels}。",
        "・感じている症状やトラブルは、必ず医療機関・弁護士・公的機関などの専門窓口へご相談ください。",
    ]
    for topic in sorted(topics):
        guidance = SENSITIVE_TOPIC_GUIDANCE.get(topic)
        if guidance:
            lines.append(f"・{guidance}")

    lines.append(
        "占いとしては、気持ちや状況の整理、日常でできそうなセルフケアや次の一歩に焦点を当てましょう。"
    )
    lines.append("禁止/注意テーマの一覧は /help または /terms から確認できます。")
    return "\n".join(lines)


async def respond_with_safety_notice(message: Message, user_query: str) -> bool:
    topics = classify_sensitive_topics(user_query)
    if not topics:
        return False

    user_id = message.from_user.id if message.from_user else None
    reset_conversation_state(user_id)
    mark_user_active(user_id)
    await message.answer(
        build_sensitive_topic_notice(topics), reply_markup=ensure_quick_menu()
    )
    return True


def _is_stale_query_error(error: Exception | str) -> bool:
    message = str(error).lower()
    stale_fragments = [
        "query is too old",
        "query id is invalid",
        "query is too old and response time expired",
    ]
    return any(fragment in message for fragment in stale_fragments)


async def _safe_answer_callback(query: CallbackQuery, *args, **kwargs) -> None:
    try:
        await query.answer(*args, **kwargs)
    except TelegramBadRequest as exc:
        if _is_stale_query_error(exc):
            await _handle_stale_interaction(
                query,
                user_id=query.from_user.id if query.from_user else None,
                sku=None,
                payload=query.data,
            )
            return
        logger.exception(
            "TelegramBadRequest while answering callback query",
            extra={"callback_data": query.data, "error": str(exc)},
        )
    except Exception:
        logger.exception("Failed to answer callback query", extra={"callback_data": query.data})


def _parse_invoice_payload(payload: str) -> tuple[str | None, int | None]:
    try:
        payload_data = json.loads(payload)
    except json.JSONDecodeError:
        return None, None

    if not isinstance(payload_data, dict):
        return None, None

    sku = payload_data.get("sku")
    user_id_raw = payload_data.get("user_id")
    try:
        user_id = int(user_id_raw) if user_id_raw is not None else None
    except (TypeError, ValueError):
        user_id = None

    return (str(sku) if sku is not None else None, user_id)


CARD_LINE_PREFIX = "《カード》："

_META_HEADING_PATTERNS = (
    r"^(まとめとして|結論として|総括として|総評として|まとめると|結論から言うと)[、,:：]?\s*",
)


def _strip_meta_prefix(text: str) -> str:
    cleaned = text
    for pattern in _META_HEADING_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    return cleaned.strip()


def _inject_position_headings(
    lines: list[str], position_labels: Sequence[str] | None
) -> list[str]:
    if not position_labels:
        return lines

    bracketed_labels = [f"【{label}】" for label in position_labels if label]
    if not bracketed_labels:
        return lines

    formatted_text = "\n".join(lines)
    missing_labels = [label for label in bracketed_labels if label not in formatted_text]
    if not missing_labels:
        return lines

    try:
        card_line_index = next(
            idx for idx, line in enumerate(lines) if CARD_LINE_PREFIX in line
        )
    except StopIteration:
        card_line_index = None

    insert_index = (card_line_index + 1) if card_line_index is not None else len(lines)
    new_lines: list[str] = []
    new_lines.extend(lines[:insert_index])

    if new_lines and new_lines[-1] != "":
        new_lines.append("")
    new_lines.extend(missing_labels)
    if insert_index < len(lines) and lines[insert_index] != "":
        new_lines.append("")

    new_lines.extend(lines[insert_index:])
    return new_lines


def _compress_trailing_text(trailing_text: str) -> str:
    normalized = _strip_meta_prefix(trailing_text)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return ""

    sentences = re.split(r"(?<=[。．！？!？])\s*", normalized)
    sentences = [s for s in sentences if s]
    if not sentences:
        return normalized

    compressed = "".join(sentences[:2]).strip()
    return compressed


def _finalize_tarot_lines(lines: list[str]) -> list[str]:
    bullet_indexes = [idx for idx, line in enumerate(lines) if line.lstrip().startswith("・")]
    if bullet_indexes:
        limited_lines: list[str] = []
        bullet_seen = 0
        for idx, line in enumerate(lines):
            if idx in bullet_indexes:
                bullet_seen += 1
                if bullet_seen > 4:
                    continue
            limited_lines.append(line)
        lines = limited_lines

        bullet_indexes = [idx for idx, line in enumerate(lines) if line.lstrip().startswith("・")]
        last_bullet_idx = bullet_indexes[-1]
        trailing = lines[last_bullet_idx + 1 :]
        while trailing and trailing[0] == "":
            trailing.pop(0)
        trailing_text = " ".join([t for t in trailing if t]).strip()
        closing_line = _compress_trailing_text(trailing_text) if trailing_text else ""
        lines = lines[: last_bullet_idx + 1]
        if closing_line:
            lines.append(closing_line)

    return lines


def format_tarot_answer(
    text: str,
    card_line: str | None = None,
    *,
    position_labels: Sequence[str] | None = None,
) -> str:
    content = (text or "").strip()
    if not content:
        return "占い結果をうまく作成できませんでした。もう一度占わせてください。"

    content = content.replace("🃏", "")
    content = re.sub(r"(\n\s*){3,}", "\n\n", content)
    lines = [line.rstrip() for line in content.splitlines()]

    normalized_lines: list[str] = []
    card_line_found = False
    for line in lines:
        cleaned = re.sub(r"^結論：\s*", "", line).strip()
        cleaned = re.sub(r"^[0-9]+[\.．]\s*", "", cleaned)
        cleaned = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "", cleaned)
        if re.fullmatch(r"[-・\s]*メインメッセージ[:：]?\s*", cleaned):
            continue
        cleaned = cleaned.replace("【メインメッセージ】", "")
        cleaned = _strip_meta_prefix(cleaned)
        cleaned = re.sub(r"^カード：", "引いたカード：", cleaned)
        cleaned = re.sub(r"^引いたカード[：:]", CARD_LINE_PREFIX, cleaned)
        cleaned = re.sub(r"^《?カード》?[：:]", CARD_LINE_PREFIX, cleaned)
        if CARD_LINE_PREFIX in cleaned:
            if card_line:
                cleaned = card_line
            if card_line_found:
                continue
            card_line_found = True
        normalized_lines.append(cleaned)

    if not card_line_found and card_line:
        intro = [ln for ln in normalized_lines[:2] if ln]
        rest = normalized_lines[2:]
        normalized_lines = intro
        if intro:
            normalized_lines.append("")
        normalized_lines.append(card_line)
        if rest:
            normalized_lines.append("")
            normalized_lines.extend(rest)

    compacted: list[str] = []
    for line in normalized_lines:
        if line == "" and compacted and compacted[-1] == "":
            continue
        compacted.append(line)

    while compacted and compacted[0] == "":
        compacted.pop(0)
    while compacted and compacted[-1] == "":
        compacted.pop()

    compacted = _finalize_tarot_lines(compacted)
    compacted = _inject_position_headings(compacted, position_labels)
    formatted = "\n".join(compacted)
    if len(formatted) > 1400:
        formatted = formatted[:1380].rstrip() + "…"
    return formatted


def format_long_answer(
    text: str,
    mode: str,
    card_line: str | None = None,
    *,
    position_labels: Sequence[str] | None = None,
) -> str:
    if mode == "tarot":
        return format_tarot_answer(text, card_line, position_labels=position_labels)

    content = (text or "").strip()
    if not content:
        return "少し情報が足りないようです。もう一度教えてくださいね。"

    lines = [
        re.sub(r"^結論：?\s*", "", line)
        for line in content.splitlines()
    ]
    cleaned_lines: list[str] = []
    for line in lines:
        stripped = re.sub(r"^[0-9]+[\.．]\s*", "", line)
        stripped = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]\s*", "", stripped)
        stripped = re.sub(r"^✅\s*", "", stripped)
        stripped = stripped.replace("次の一手", "").strip()
        if stripped or (cleaned_lines and cleaned_lines[-1] != ""):
            cleaned_lines.append(stripped)

    while cleaned_lines and cleaned_lines[0] == "":
        cleaned_lines.pop(0)
    while cleaned_lines and cleaned_lines[-1] == "":
        cleaned_lines.pop()

    content = "\n".join(cleaned_lines) if cleaned_lines else ""
    if not content:
        return "少し情報が足りないようです。もう一度教えてくださいね。"

    content = re.sub(r"(\n\s*){3,}", "\n\n", content)
    if len(content) > 1400:
        content = content[:1380].rstrip() + "…"
    return content


def split_text_for_sending(text: str, *, limit: int = 3800) -> list[str]:
    if len(text) <= limit:
        return [text]
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(para) > limit:
                while len(para) > limit:
                    chunks.append(para[:limit])
                    para = para[limit:]
                if para:
                    current = para
                else:
                    current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


async def send_long_text(
    chat_id: int,
    text: str,
    *,
    reply_to: int | None = None,
    edit_target: Message | None = None,
    reply_markup_first: InlineKeyboardMarkup | None = None,
    reply_markup_last: InlineKeyboardMarkup | None = None,
) -> None:
    chunks = split_text_for_sending(text)
    first_chunk, *rest = chunks
    first_markup = reply_markup_last if not rest else reply_markup_first
    if edit_target:
        try:
            await edit_target.edit_text(first_chunk, reply_markup=first_markup)
        except Exception:
            await bot.send_message(
                chat_id,
                first_chunk,
                reply_to_message_id=reply_to,
                reply_markup=first_markup,
            )
    else:
        await bot.send_message(
            chat_id,
            first_chunk,
            reply_to_message_id=reply_to,
            reply_markup=first_markup,
        )

    for index, chunk in enumerate(rest):
        is_last = index == len(rest) - 1
        markup = reply_markup_last if is_last else None
        await bot.send_message(
            chat_id,
            chunk,
            reply_to_message_id=reply_to,
            reply_markup=markup,
        )


async def _acquire_inflight(
    user_id: int | None,
    message: Message | None = None,
    *,
    busy_message: str | None = "いま鑑定中です…少し待ってね。",
) -> Callable[[], None]:
    def _noop() -> None:
        return None

    if user_id is None:
        return _noop

    lock = USER_REQUEST_LOCKS.setdefault(user_id, asyncio.Lock())
    already_locked = lock.locked()
    if already_locked and message:
        reply_text = busy_message or ""
        if reply_text:
            asyncio.create_task(message.answer(reply_text))
    await lock.acquire()
    IN_FLIGHT_USERS.add(user_id)
    logger.info(
        "Acquired user request lock",
        extra={
            "user_id": user_id,
            "queued": already_locked,
        },
    )

    def _release() -> None:
        if lock.locked():
            lock.release()
        IN_FLIGHT_USERS.discard(user_id)
        logger.info(
            "Released user request lock",
            extra={
                "user_id": user_id,
            },
        )

    return _release


def _mark_recent_handled(message: Message) -> bool:
    message_id = getattr(message, "message_id", None)
    if message_id is None:
        return True
    key = (message.chat.id, message_id)
    if key in RECENT_HANDLED:
        return False
    if len(RECENT_HANDLED_ORDER) >= RECENT_HANDLED_ORDER.maxlen:
        oldest = RECENT_HANDLED_ORDER.popleft()
        RECENT_HANDLED.discard(oldest)
    RECENT_HANDLED.add(key)
    RECENT_HANDLED_ORDER.append(key)
    return True


def _usage_today(now: datetime) -> datetime.date:
    return now.astimezone(USAGE_TIMEZONE).date()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cleanup_pending_purchases(now_monotonic: float) -> None:
    expired_keys = [
        key for key, ts in PENDING_PURCHASES.items() if now_monotonic - ts > PURCHASE_DEDUP_TTL_SECONDS
    ]
    for key in expired_keys:
        PENDING_PURCHASES.pop(key, None)


def _check_purchase_dedup(user_id: int, product_sku: str) -> bool:
    now_ts = monotonic()
    _cleanup_pending_purchases(now_ts)
    key = (user_id, product_sku)
    last_request = PENDING_PURCHASES.get(key)
    if last_request and now_ts - last_request < PURCHASE_DEDUP_TTL_SECONDS:
        return True
    PENDING_PURCHASES[key] = now_ts
    return False


async def _safe_answer_pre_checkout(
    pre_checkout_query: PreCheckoutQuery, *, ok: bool, error_message: str | None = None
) -> None:
    try:
        await bot.answer_pre_checkout_query(
            pre_checkout_query.id,
            ok=ok,
            error_message=error_message,
        )
    except TelegramBadRequest as exc:
        if _is_stale_query_error(exc):
            await _handle_stale_interaction(
                pre_checkout_query,
                user_id=pre_checkout_query.from_user.id if pre_checkout_query.from_user else None,
                sku=None,
                payload=pre_checkout_query.invoice_payload,
                event_type="stale_pre_checkout",
            )
            return
        logger.exception(
            "TelegramBadRequest while answering pre_checkout_query",
            extra={"payload": pre_checkout_query.invoice_payload, "error": str(exc)},
        )
    except Exception:
        logger.exception(
            "Failed to answer pre_checkout_query",
            extra={"payload": pre_checkout_query.invoice_payload},
        )


def _build_charge_retry_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒チャージへ", callback_data="nav:charge")],
            [InlineKeyboardButton(text="📊ステータスを見る", callback_data="nav:status")],
        ]
    )


def _safe_log_payment_event(
    *, user_id: int | None, event_type: str, sku: str | None = None, payload: str | None = None
) -> None:
    if user_id is None:
        return
    try:
        log_payment_event(user_id=user_id, event_type=event_type, sku=sku, payload=payload)
    except Exception:
        logger.exception(
            "Failed to log payment event",
            extra={"user_id": user_id, "event_type": event_type, "payload": payload},
        )


def _safe_log_audit(
    *,
    action: str,
    actor_user_id: int | None,
    target_user_id: int | None,
    payload: str | None,
    status: str,
) -> None:
    if actor_user_id is None:
        return
    try:
        log_audit(
            action=action,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            payload=payload,
            status=status,
        )
    except Exception:
        logger.exception(
            "Failed to write audit log",
            extra={
                "action": action,
                "actor_user_id": actor_user_id,
                "target_user_id": target_user_id,
                "status": status,
            },
        )


async def _handle_stale_interaction(
    event: CallbackQuery | PreCheckoutQuery,
    *,
    user_id: int | None,
    sku: str | None,
    payload: str | None,
    event_type: str = "stale_callback",
) -> None:
    chat_id: int | None = None
    if isinstance(event, CallbackQuery) and event.message and event.message.chat:
        chat_id = event.message.chat.id
    _safe_log_payment_event(user_id=user_id, event_type=event_type, sku=sku, payload=payload)
    if user_id is None and chat_id is None:
        logger.warning("Stale interaction detected but no user/chat to notify", extra={"payload": payload})
        return
    try:
        target = chat_id if chat_id is not None else user_id
        await bot.send_message(target, STALE_CALLBACK_MESSAGE, reply_markup=_build_charge_retry_keyboard())
    except Exception:
        logger.exception("Failed to notify user about stale interaction", extra={"payload": payload, "user_id": user_id})


def build_general_chat_messages(user_query: str) -> list[dict[str, str]]:
    """通常チャットモードの system prompt を組み立てる。"""
    return [
        {"role": "system", "content": CONSULT_SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]


async def call_openai_with_retry(messages: Iterable[dict[str, str]]) -> tuple[str, bool]:
    prepared_messages = list(messages)
    max_attempts = 3
    base_delay = 1.5

    for attempt in range(1, max_attempts + 1):
        try:
            completion = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini", messages=prepared_messages
                ),
            )
            answer = completion.choices[0].message.content
            return postprocess_llm_text(answer), False
        except (AuthenticationError, PermissionDeniedError, BadRequestError) as exc:
            logger.exception("Fatal OpenAI error: %s", exc)
            return (
                "システム側の設定で問題が起きています。"
                "少し時間をおいて、もう一度試してもらえますか？",
                True,
            )
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            logger.warning(
                "Transient OpenAI error on attempt %s/%s: %s",
                attempt,
                max_attempts,
                exc,
                exc_info=True,
            )
            if attempt == max_attempts:
                break
        except APIError as exc:
            logger.warning(
                "APIError on attempt %s/%s (status=%s): %s",
                attempt,
                max_attempts,
                getattr(exc, "status", None),
                exc,
                exc_info=True,
            )
            if getattr(exc, "status", 500) >= 500 and attempt < max_attempts:
                pass
            else:
                return (
                    "占いの処理で問題が発生しました。"
                    "少し時間をおいて、もう一度試していただけるとうれしいです。",
                    True,
                )

        delay = base_delay * (2 ** (attempt - 1))
        delay += random.uniform(0, 0.5)
        await asyncio.sleep(delay)

    return (
        "通信がうまくいかなかったみたいです。"
        "少し時間をおいて、もう一度試してもらえますか？",
        False,
    )


def _preview_text(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def get_chat_id(message: Message) -> int | None:
    chat = getattr(message, "chat", None)
    if chat and getattr(chat, "id", None) is not None:
        return chat.id
    if message.from_user:
        return message.from_user.id
    return None


def get_user_mode(user_id: int | None) -> str:
    if user_id is None:
        return "consult"
    return USER_MODE.get(user_id, "consult")


def set_user_mode(user_id: int | None, mode: str) -> None:
    if user_id is None:
        return
    USER_MODE[user_id] = mode
    if mode != "tarot":
        TAROT_FLOW.pop(user_id, None)


def set_tarot_flow(user_id: int | None, state: str | None) -> None:
    if user_id is None:
        return
    TAROT_FLOW[user_id] = state
    if state is None:
        TAROT_FLOW.pop(user_id, None)


def set_tarot_theme(user_id: int | None, theme: str) -> None:
    if user_id is None:
        return
    TAROT_THEME[user_id] = theme


def get_tarot_theme(user_id: int | None) -> str:
    if user_id is None:
        return DEFAULT_THEME
    return TAROT_THEME.get(user_id, DEFAULT_THEME)


def reset_tarot_state(user_id: int | None) -> None:
    if user_id is None:
        return
    TAROT_FLOW.pop(user_id, None)
    TAROT_THEME.pop(user_id, None)


def reset_conversation_state(user_id: int | None) -> None:
    if user_id is None:
        return
    USER_MODE.pop(user_id, None)
    reset_tarot_state(user_id)
    USER_STATE_LAST_ACTIVE.pop(user_id, None)


def mark_user_active(user_id: int | None, *, now: datetime | None = None) -> None:
    if user_id is None:
        return
    USER_STATE_LAST_ACTIVE[user_id] = now or utcnow()


async def reset_state_if_inactive(message: Message, *, now: datetime) -> bool:
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        return False
    last_active = USER_STATE_LAST_ACTIVE.get(user_id)
    if last_active is None:
        return False
    if now - last_active < STATE_TIMEOUT:
        return False
    reset_conversation_state(user_id)
    await message.answer(
        "しばらく操作がなかったため状態をリセットしました。/start か /help からやり直してください。",
        reply_markup=base_menu_kb(),
    )
    return True


def reset_state_for_explicit_command(user_id: int | None) -> None:
    if user_id is None:
        return
    reset_conversation_state(user_id)


def get_tarot_theme_label(theme: str) -> str:
    return TAROT_THEME_LABELS.get(theme, TAROT_THEME_LABELS[DEFAULT_THEME])


def format_next_reset(now: datetime) -> str:
    next_reset = datetime.combine(
        _usage_today(now) + timedelta(days=1), time(0, 0), tzinfo=USAGE_TIMEZONE
    )
    return next_reset.strftime("%m/%d %H:%M JST")


def build_tarot_theme_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❤️恋愛", callback_data="tarot_theme:love")],
            [InlineKeyboardButton(text="💍結婚", callback_data="tarot_theme:marriage")],
            [InlineKeyboardButton(text="💼仕事", callback_data="tarot_theme:work")],
            [InlineKeyboardButton(text="🌉人生", callback_data="tarot_theme:life")],
        ]
    )


def build_upgrade_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="3枚で深掘り（有料）", callback_data="upgrade_to_three")]
        ]
    )


async def prompt_tarot_mode(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "tarot")
    set_tarot_theme(user_id, DEFAULT_THEME)
    set_tarot_flow(user_id, "awaiting_theme")
    mark_user_active(user_id)
    await message.answer(TAROT_THEME_PROMPT, reply_markup=base_menu_kb())
    await message.answer("テーマを選んでください👇", reply_markup=build_tarot_theme_keyboard())


async def prompt_consult_mode(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "consult")
    reset_tarot_state(user_id)
    mark_user_active(user_id)
    await message.answer(CONSULT_MODE_PROMPT, reply_markup=base_menu_kb())


async def prompt_charge_menu(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "charge")
    mark_user_active(user_id)
    await message.answer(CHARGE_MODE_PROMPT, reply_markup=base_menu_kb())
    await send_store_menu(message)


async def prompt_status(message: Message, *, now: datetime) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "status")
    mark_user_active(user_id, now=now)
    if user_id is None:
        await message.answer(
            "ユーザー情報を確認できませんでした。個別チャットからお試しくださいませ。",
            reply_markup=base_menu_kb(),
        )
        return
    user = get_user_with_default(user_id) or ensure_user(user_id, now=now)
    await message.answer(format_status(user, now=now), reply_markup=base_menu_kb())


COMMAND_SPREAD_MAP: dict[str, Spread] = {
    "/love1": ONE_CARD,
    "/read1": ONE_CARD,
    "/love3": THREE_CARD_TIME_AXIS,
    "/read3": THREE_CARD_TIME_AXIS,
    "/hexa": HEXAGRAM,
    "/celtic": CELTIC_CROSS,
}


PAID_SPREAD_IDS: set[str] = {THREE_CARD_TIME_AXIS.id, HEXAGRAM.id, CELTIC_CROSS.id}

SPREAD_TICKET_COLUMNS: dict[str, TicketColumn] = {
    THREE_CARD_TIME_AXIS.id: "tickets_3",
    HEXAGRAM.id: "tickets_7",
    CELTIC_CROSS.id: "tickets_10",
}

TICKET_SKU_TO_COLUMN: dict[str, TicketColumn] = {
    "TICKET_3": "tickets_3",
    "TICKET_7": "tickets_7",
    "TICKET_10": "tickets_10",
}


SHORT_TAROT_OUTPUT_RULES = [
    "引いたカード名（正逆）と位置を最初に短く伝える。",
    "結論とアドバイスを中心に180〜260文字でまとめる。",
    "専門領域は専門家相談を促し、断定を避けてやさしく。",
]


def _days_since_first_seen(user: UserRecord, now: datetime) -> int:
    return (_usage_today(now) - _usage_today(user.first_seen)).days


def _trial_day_number(user: UserRecord, now: datetime) -> int:
    return _days_since_first_seen(user, now) + 1


def _general_chat_trial_days_left(user: UserRecord, now: datetime) -> int:
    used_days = _days_since_first_seen(user, now)
    return max(0, FREE_GENERAL_CHAT_DAYS - (used_days + 1))


def _is_in_general_chat_trial(user: UserRecord, now: datetime) -> bool:
    return _days_since_first_seen(user, now) < FREE_GENERAL_CHAT_DAYS


def _evaluate_one_oracle_access(
    *, user: UserRecord, user_id: int, now: datetime
) -> tuple[bool, bool, UserRecord]:
    latest_user = get_user(user_id, now=now) or user
    is_admin = is_admin_user(user_id)
    has_pass = effective_has_pass(user_id, latest_user, now=now)
    date_key = _usage_today(now).isoformat()
    memory_key = (user_id, date_key)
    base_count = ONE_ORACLE_MEMORY.get(memory_key, latest_user.one_oracle_count_today)

    limit = (
        FREE_ONE_ORACLE_TRIAL_PER_DAY
        if _is_in_general_chat_trial(latest_user, now)
        else FREE_ONE_ORACLE_POST_TRIAL_PER_DAY
    )

    if is_admin:
        return True, False, latest_user

    if not has_pass and base_count >= limit:
        return False, False, latest_user

    new_count = base_count + 1
    ONE_ORACLE_MEMORY[memory_key] = new_count
    updated_user = increment_one_oracle_count(user_id, now=now)
    short_response = not has_pass and new_count <= limit
    return True, short_response, updated_user


def choose_spread(_: str) -> Spread:
    return ONE_CARD


def parse_spread_command(text: str) -> tuple[Spread | None, str]:
    if not text:
        return None, ""

    parts = text.split(maxsplit=1)
    command = parts[0].lower()
    spread = COMMAND_SPREAD_MAP.get(command)
    if not spread:
        return None, text

    remainder = parts[1].strip() if len(parts) > 1 else ""
    return spread, remainder


def is_paid_spread(spread: Spread) -> bool:
    return spread.id in PAID_SPREAD_IDS


def is_admin_user(user_id: int | None) -> bool:
    return user_id is not None and user_id in ADMIN_USER_IDS


def get_bot_display_name() -> str:
    return "akolasia_tarot_bot"


def get_support_email() -> str:
    env_email = os.getenv("SUPPORT_EMAIL")
    if env_email:
        return env_email
    return SUPPORT_EMAIL


def build_paid_hint(text: str) -> str | None:
    hints = ["3枚", "３枚", "三枚", "3card", "3 カード", "ヘキサ", "ケルト", "十字", "7枚", "７枚", "10枚", "１０枚"]
    if any(hint in text for hint in hints):
        return "複数枚はコマンド指定です：/read3 /hexa /celtic（無料は『占って』で1枚）"
    return None


def determine_action_count(user_id: int | None, message_id: int | None) -> int:
    seed = (user_id or 0) * 31 + (message_id or 0)
    rng = random.Random(seed)
    roll = rng.random()
    if roll < 0.15:
        return 4
    return 2 if rng.random() < 0.5 else 3


async def execute_tarot_request(
    message: Message,
    user_query: str,
    *,
    spread: Spread | None = None,
    guidance_note: str | None = None,
    theme: str | None = None,
) -> None:
    now = utcnow()
    user_id = message.from_user.id if message.from_user else None
    user: UserRecord | None = ensure_user(user_id, now=now) if user_id is not None else None
    spread_to_use = spread or choose_spread(user_query)
    paywall_triggered = False
    short_response = False
    allowed = True
    effective_theme = theme or get_tarot_theme(user_id)

    if await respond_with_safety_notice(message, user_query):
        logger.info(
            "Safety notice triggered",
            extra={
                "mode": "tarot",
                "user_id": user_id,
                "admin_mode": is_admin_user(user_id),
                "text_preview": _preview_text(user_query),
                "route": "tarot_safety",
                "tarot_flow": TAROT_FLOW.get(user_id),
                "tarot_theme": effective_theme,
                "paywall_triggered": paywall_triggered,
            },
        )
        return

    if spread_to_use == ONE_CARD:
        if user_id is not None and user is not None:
            allowed, short_response, user = _evaluate_one_oracle_access(
                user=user, user_id=user_id, now=now
            )
    if not allowed:
        paywall_triggered = True
        await message.answer(
            "本日の無料枠は使い切りました。続けるには🛒チャージから"
            "チケット/パスを選んでください。次回リセット: "
            f"{format_next_reset(now)}",
        )
        logger.info(
            "Tarot request blocked",
            extra={
                "mode": "tarot",
                "user_id": user_id,
                "admin_mode": is_admin_user(user_id),
                "text_preview": _preview_text(user_query),
                "route": "tarot",
                "tarot_flow": TAROT_FLOW.get(user_id),
                "tarot_theme": effective_theme,
                "paywall_triggered": paywall_triggered,
            },
        )
        return
    elif PAYWALL_ENABLED and is_paid_spread(spread_to_use):
        has_pass = effective_has_pass(user_id, user, now=now)
        if not has_pass:
            if user_id is None or not consume_ticket_for_spread(user_id, spread_to_use):
                paywall_triggered = True
                await message.answer(
                    "こちらは有料メニューです。\n"
                    "ご購入は /buy からお進みいただけます（無料の1枚引きは /read1 または『占って』でお楽しみください）。"
                )
                logger.info(
                    "Tarot request blocked",
                    extra={
                    "mode": "tarot",
                    "user_id": user_id,
                    "admin_mode": is_admin_user(user_id),
                    "text_preview": _preview_text(user_query),
                    "route": "tarot",
                    "tarot_flow": TAROT_FLOW.get(user_id),
                    "tarot_theme": effective_theme,
                    "paywall_triggered": paywall_triggered,
                },
            )
            return

    logger.info(
        "Handling message",
        extra={
            "mode": "tarot",
            "user_id": user_id,
            "admin_mode": is_admin_user(user_id),
            "text_preview": _preview_text(user_query),
            "route": "tarot",
            "tarot_flow": TAROT_FLOW.get(user_id),
            "tarot_theme": effective_theme,
            "paywall_triggered": paywall_triggered,
        },
    )

    await handle_tarot_reading(
        message,
        user_query=user_query,
        spread=spread_to_use,
        guidance_note=guidance_note or build_paid_hint(user_query),
        short_response=short_response,
    )


def get_start_text() -> str:
    bot_name = get_bot_display_name()
    return (
        f"こんにちは、AIタロット占いボット {bot_name} です。\n"
        "無料のショート鑑定は1日2回までお試しいただけます（/read1 がショート）。\n"
        "複数枚なら /read3 などのコマンドから始められます。\n"
        "下のボタンから「🎩占い」か「💬相談」を選んでください。\n"
        "使い方は /help で確認できます。"
    )


def get_store_intro_text() -> str:
    def _label(sku: str) -> str:
        product = get_product(sku)
        if not product:
            return sku
        return f"{product.title}（{product.price_stars}⭐️）"

    ticket_3 = _label("TICKET_3")
    ticket_7 = _label("TICKET_7")
    ticket_10 = _label("TICKET_10")
    pass_7d = _label("PASS_7D")
    pass_30d = _label("PASS_30D")

    return (
        "ご利用ありがとうございます。目的に合わせてお選びください。\n"
        "\n"
        "🔮占いチケット\n"
        f"・初めて/状況整理：{ticket_3}\n"
        f"・深掘りしたい：{ticket_7}\n"
        f"・じっくり決めたい：{ticket_10}\n"
        "\n"
        "💬相談パス（相談チャットが開放されます）\n"
        f"・短期で試す：{pass_7d}\n"
        f"・じっくり続ける：{pass_30d}\n"
        "\n"
        "パスをお持ちの方はそのまま占いに戻れば使えます。二重購入は不要です。\n"
        "StarsはTelegram内の残高に保持され、余った分も次回にお使いいただけます。\n"
        "決済はTelegram Stars (XTR) です。ゆっくりお進みください。\n"
        "価格（⭐️）はボタンでもご確認いただけます。"
    )


def consume_ticket_for_spread(user_id: int, spread: Spread) -> bool:
    column = SPREAD_TICKET_COLUMNS.get(spread.id)
    if not column:
        return False
    return consume_ticket(user_id, ticket=column)


def format_status(user: UserRecord, *, now: datetime | None = None) -> str:
    now = now or utcnow()
    pass_until = effective_pass_expires_at(user.user_id, user, now)
    has_pass = effective_has_pass(user.user_id, user, now=now)
    status_title = STATUS_MODE_PROMPT
    admin_mode = is_admin_user(user.user_id)
    if admin_mode:
        status_title = "📊現在のご利用状況（管理者モード）です。"
    trial_days_left = _general_chat_trial_days_left(user, now)
    trial_day = _trial_day_number(user, now)
    general_remaining = max(
        FREE_GENERAL_CHAT_PER_DAY - user.general_chat_count_today, 0
    )
    one_oracle_limit = (
        FREE_ONE_ORACLE_TRIAL_PER_DAY
        if _is_in_general_chat_trial(user, now)
        else FREE_ONE_ORACLE_POST_TRIAL_PER_DAY
    )
    one_remaining = max(one_oracle_limit - user.one_oracle_count_today, 0)

    general_line: str
    if has_pass:
        general_line = "パス有効中：相談チャットは回数無制限でご利用いただけます。"
    elif trial_days_left > 0:
        general_line = (
            f"trialあと{trial_days_left}日（今日の残り {general_remaining} 通）"
            "\n・6日目以降はパス限定になります。"
        )
    else:
        general_line = "パス未購入のため相談チャットは利用できません。/buy でご検討ください。"

    pass_label: str
    if pass_until:
        remaining_days = (_usage_today(pass_until) - _usage_today(now)).days
        remaining_hint = f"（あと{remaining_days}日）" if remaining_days >= 0 else ""
        pass_label = f"{pass_until.astimezone(USAGE_TIMEZONE).strftime('%Y-%m-%d %H:%M JST')} {remaining_hint}"
        if admin_mode:
            pass_label = f"{pass_label}（管理者）"
    else:
        pass_label = "なし"

    lines = [
        status_title,
        f"・trial: 初回利用から{trial_day}日目",
        f"・パス有効期限: {pass_label}",
        f"・ワンオラクル無料枠: 1日{one_oracle_limit}回（本日の残り {one_remaining} 回）",
        f"・相談チャット: {general_line}",
        f"・3枚チケット: {user.tickets_3}枚",
        f"・7枚チケット: {user.tickets_7}枚",
        f"・10枚チケット: {user.tickets_10}枚",
        f"・画像オプション: {'有効' if user.images_enabled else '無効'}",
        f"・無料枠/カウントの次回リセット: {format_next_reset(now)}",
    ]
    latest_payment = get_latest_payment(user.user_id)
    if latest_payment:
        product = get_product(latest_payment.sku)
        label = product.title if product else latest_payment.sku
        purchased_at = latest_payment.created_at.astimezone(USAGE_TIMEZONE).strftime("%Y-%m-%d %H:%M JST")
        lines.append(f"・直近の購入: {label} / SKU: {latest_payment.sku}（付与: {purchased_at}）")
    if admin_mode:
        lines.insert(1, "・管理者権限: あり（課金の制限を受けません）")
    return "\n".join(lines)


def build_unlock_text(product: Product, user: UserRecord) -> str:
    now = utcnow()
    if product.sku in TICKET_SKU_TO_COLUMN:
        column = TICKET_SKU_TO_COLUMN[product.sku]
        balance = getattr(user, column)
        return f"{product.title}を追加しました。現在の残り枚数は {balance} 枚です。"

    if product.sku.startswith("PASS_"):
        until = user.premium_until or user.pass_until
        duration = "7日パス" if product.sku == "PASS_7D" else "30日パス"
        if until:
            until_local = until.astimezone(USAGE_TIMEZONE)
            remaining_days = (_usage_today(until) - _usage_today(now)).days
            remaining_hint = f"（あと{remaining_days}日）" if remaining_days >= 0 else ""
            until_text = until_local.strftime("%Y-%m-%d %H:%M JST")
        else:
            until_text = "有効期限を更新しました。"
            remaining_hint = ""
        return (
            f"{duration}を付与しました。\n"
            f"有効期限: {until_text}{remaining_hint}"
        )

    if product.sku == "ADDON_IMAGES":
        return "画像付きのオプションを有効化しました。これからの占いにやさしい彩りを添えますね。"

    return "ご購入ありがとうございます。必要に応じてサポートまでお知らせください。"


def build_tarot_messages(
    *,
    spread: Spread,
    user_query: str,
    drawn_cards: list[dict[str, str]],
    short: bool = False,
    theme: str | None = None,
    action_count: int | None = None,
) -> list[dict[str, str]]:
    is_time_axis = spread.id == THREE_CARD_TIME_AXIS.id
    rules = TIME_AXIS_TAROT_RULES if is_time_axis else SHORT_TAROT_OUTPUT_RULES if short else TAROT_OUTPUT_RULES
    rules_text = "\n".join(f"- {rule}" for rule in rules)
    tarot_system_prompt = f"{get_tarot_system_prompt(theme, time_axis=is_time_axis)}\n出力ルール:\n{rules_text}"
    theme_focus = theme_instructions(theme)
    if is_time_axis:
        action_count_text = "- 箇条書きは未来パートにのみ最大3点まで。過去と現在では使わない。"
        scope_text = "- 時間の目安が無い場合は前後3か月の流れとして触れる。"
        format_hint = (
            "過去・現在・未来の時間軸リーディングです。見出しや章ラベルを使わず、次の並びと改行を必ず守ってください:\n"
            f"{TIME_AXIS_FIXED_OUTPUT_FORMAT}\n"
            f"{action_count_text}\n"
            f"{scope_text}\n"
            "- カード名は各ブロックの《カード》行で必ず書く。🃏などの絵文字は禁止。\n"
            f"- テーマ別フォーカス: {theme_focus}"
        )
    else:
        if action_count is not None:
            if action_count == 4:
                action_count_text = (
                    "- 次の一手は必ず4個。内容が薄い場合は各項目を短くしないで具体化する。"
                )
            elif action_count in {2, 3}:
                action_count_text = (
                    f"- 次の一手は必ず{action_count}個。4個は禁止。必要な要素は各項目に統合して良い。"
                )
            else:
                action_count_text = "- 次の一手はシステムの指示個数を守り、必要でも4個までに抑える。"
        else:
            action_count_text = "- 次の一手は2〜3個を基本に、必要なときだけ4個まで。"
        format_hint = (
            "必ず次の順序と改行で、見出しや絵文字を使わずに書いてください:\n"
            f"{TAROT_FIXED_OUTPUT_FORMAT}\n"
            f"{action_count_text}\n"
            "- 1枚引きは350〜650字、3枚以上は550〜900字を目安に、1400文字以内に収める。\n"
            "- カード名は「《カード》：」行で1回だけ伝える。🃏などの絵文字は禁止。\n"
            f"- テーマ別フォーカス: {theme_focus}"
        )

    tarot_payload = {
        "spread_id": spread.id,
        "spread_name_ja": spread.name_ja,
        "positions": drawn_cards,
        "user_question": user_query,
    }

    return [
        {"role": "system", "content": tarot_system_prompt},
        {"role": "system", "content": format_hint},
        {"role": "assistant", "content": json.dumps(tarot_payload, ensure_ascii=False, indent=2)},
        {"role": "user", "content": user_query},
    ]


def format_drawn_cards(drawn_cards: list[dict[str, str]]) -> str:
    if not drawn_cards:
        return f"{CARD_LINE_PREFIX}カード情報を取得できませんでした。"

    card_labels = []
    for item in drawn_cards:
        card = item.get("card", {})
        card_name = card.get("name_ja") or "不明なカード"
        orientation = card.get("orientation_label_ja")
        card_label = f"{card_name}（{orientation}）" if orientation else card_name
        position_label = item.get("label_ja")
        if position_label and position_label.strip() != "メインメッセージ":
            card_labels.append(f"{card_label} - {position_label}")
        else:
            card_labels.append(card_label)
    return CARD_LINE_PREFIX + "、".join(card_labels)


def ensure_tarot_response_prefixed(answer: str, heading: str) -> str:
    if answer.lstrip().startswith(CARD_LINE_PREFIX):
        return answer
    return f"{heading}\n{answer}" if heading else answer


async def rewrite_chat_response(original: str) -> tuple[str, bool]:
    rewrite_prompt = (
        "次の文章から、タロット・カード・占いに関する言及をすべて取り除いて日本語で書き直してください。"
        "丁寧で落ち着いた敬語を維持し、相談の意図や励ましは残してください。"
    )

    messages = [
        {"role": "system", "content": rewrite_prompt},
        {"role": "user", "content": original},
    ]

    return await call_openai_with_retry(messages)


async def ensure_general_chat_safety(
    answer: str, *, rewrite_func=rewrite_chat_response
) -> str:
    if not contains_tarot_like(answer):
        return answer

    try:
        rewritten, fatal = await rewrite_func(answer)
    except Exception:
        logger.exception("Unexpected error during chat rewrite")
        rewritten, fatal = "", False

    if rewritten and not fatal and not contains_tarot_like(rewritten):
        return rewritten

    cleaned = strip_tarot_sentences(rewritten or answer)
    if cleaned:
        return cleaned

    return "落ち着いてお話ししましょう。あなたの気持ちを大切に受け止めます。"


TERMS_CALLBACK_SHOW = "terms:show"
TERMS_CALLBACK_AGREE = "terms:agree"
TERMS_CALLBACK_AGREE_AND_BUY = "terms:agree_and_buy"


def get_terms_text() -> str:
    support_email = get_support_email()
    return (
        "利用規約（抜粋）\n"
        "・18歳以上の自己責任で利用してください。\n"
        "・禁止/注意テーマ（医療/診断/薬、法律/契約/紛争、投資助言、自傷/他害）は専門家へご相談ください。\n"
        "・迷惑行為・違法行為への利用は禁止です。\n"
        "・デジタル商品につき原則返金不可ですが、不具合時は調査のうえ返金します。\n"
        f"・連絡先: {support_email}\n\n"
        "購入前に上記へ同意してください。"
    )


def get_support_text() -> str:
    support_email = get_support_email()
    return (
        "お問い合わせ窓口です。\n"
        f"・購入者サポート: {support_email}\n"
        "・一般問い合わせ: Telegram @akolasia_support\n"
        "※Telegramの一般窓口では決済トラブルは扱えません。必要な場合は /paysupport をご利用ください。"
    )


def get_pay_support_text() -> str:
    support_email = get_support_email()
    return (
        "決済トラブルの受付です。下記テンプレをコピーしてお知らせください。\n"
        "購入日時: \n"
        "商品名/SKU: \n"
        "charge_id: （表示される場合）\n"
        "支払方法: Stars / その他\n"
        "スクリーンショット: あり/なし\n"
        "確認のうえ、必要に応じて返金や付与対応を行います。\n"
        f"連絡先: {support_email}"
    )

TERMS_PROMPT_BEFORE_BUY = "購入前に /terms を確認し、同意の上でお進みください。"


def build_terms_keyboard(include_buy_option: bool = False) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="同意する", callback_data=TERMS_CALLBACK_AGREE)]]
    )


def build_terms_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="利用規約を確認", callback_data=TERMS_CALLBACK_SHOW)],
            [InlineKeyboardButton(text="同意する", callback_data=TERMS_CALLBACK_AGREE)],
            [InlineKeyboardButton(text="同意して購入へ進む", callback_data=TERMS_CALLBACK_AGREE_AND_BUY)],
        ]
    )


def build_store_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for product in iter_products():
        if product.sku == "ADDON_IMAGES" and not IMAGE_ADDON_ENABLED:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="画像追加オプション（準備中）",
                        callback_data="addon:pending",
                    )
                ]
            )
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{product.title} - {product.price_stars}⭐️",
                    callback_data=f"buy:{product.sku}"
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_purchase_followup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎩占いに戻る", callback_data="nav:menu")],
            [InlineKeyboardButton(text="📊ステータスを見る", callback_data="nav:status")],
        ]
    )


async def send_store_menu(message: Message) -> None:
    await message.answer(
        get_store_intro_text(), reply_markup=build_store_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    await message.answer(build_help_text(), reply_markup=ensure_quick_menu())


@dp.message(Command("terms"))
async def cmd_terms(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    mark_user_active(user_id)
    if user_id is not None:
        ensure_user(user_id)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip().lower() == "agree" and user_id is not None:
        set_terms_accepted(user_id)
        await message.answer(
            "利用規約への同意を記録しました。/buy からご購入いただけます。",
            reply_markup=ensure_quick_menu(),
        )
        return

    await message.answer(get_terms_text(), reply_markup=build_terms_keyboard())
    await message.answer("同意後は /buy から購入に進めます。", reply_markup=ensure_quick_menu())


@dp.callback_query(F.data == TERMS_CALLBACK_SHOW)
async def handle_terms_show(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    if query.message:
        await query.message.answer(
            get_terms_text(), reply_markup=build_terms_prompt_keyboard()
        )


@dp.callback_query(F.data == TERMS_CALLBACK_AGREE)
async def handle_terms_agree(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await _safe_answer_callback(query, "ユーザー情報を確認できませんでした。", show_alert=True)
        return

    set_terms_accepted(user_id)
    await _safe_answer_callback(query, "同意を記録しました。", show_alert=True)
    if query.message:
        await query.message.answer(
            "利用規約への同意を記録しました。/buy から購入手続きに進めます。",
            reply_markup=ensure_quick_menu(),
        )


@dp.callback_query(F.data == TERMS_CALLBACK_AGREE_AND_BUY)
async def handle_terms_agree_and_buy(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await _safe_answer_callback(query, "ユーザー情報を確認できませんでした。", show_alert=True)
        return

    set_terms_accepted(user_id)
    await _safe_answer_callback(query, "同意を記録しました。", show_alert=True)
    if query.message:
        await send_store_menu(query.message)
    else:
        await bot.send_message(
            user_id, get_store_intro_text(), reply_markup=build_store_keyboard()
        )


@dp.message(Command("support"))
async def cmd_support(message: Message) -> None:
    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    await message.answer(get_support_text(), reply_markup=ensure_quick_menu())


@dp.message(Command("paysupport"))
async def cmd_pay_support(message: Message) -> None:
    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    await message.answer(get_pay_support_text())


@dp.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    mark_user_active(user_id)
    if user_id is not None:
        ensure_user(user_id)
        if not has_accepted_terms(user_id):
            await message.answer(
                f"{TERMS_PROMPT_BEFORE_BUY}\n/terms から同意をお願いします。",
                reply_markup=build_terms_prompt_keyboard(),
            )
            return

    await prompt_charge_menu(message)


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    now = utcnow()
    await prompt_status(message, now=now)


@dp.message(Command("read1"))
async def cmd_read1(message: Message) -> None:
    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    await prompt_tarot_mode(message)


@dp.message(Command("love1"))
async def cmd_love1(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    set_user_mode(user_id, "tarot")
    set_tarot_theme(user_id, "love")
    set_tarot_flow(user_id, "awaiting_question")
    mark_user_active(user_id)
    await message.answer(build_tarot_question_prompt("love"), reply_markup=base_menu_kb())


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    set_user_mode(user_id, "consult")
    reset_tarot_state(user_id)
    mark_user_active(user_id)
    await message.answer(get_start_text(), reply_markup=base_menu_kb())


@dp.callback_query(F.data == "nav:menu")
async def handle_nav_menu(query: CallbackQuery, state: FSMContext) -> None:
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    reset_tarot_state(user_id)
    set_user_mode(user_id, "consult")
    mark_user_active(user_id)
    await state.clear()
    if query.message:
        await query.message.answer(
            "メニューに戻りました。下のボタンから選んでください。", reply_markup=base_menu_kb()
        )


@dp.callback_query(F.data == "nav:status")
async def handle_nav_status(query: CallbackQuery, state: FSMContext) -> None:
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await _safe_answer_callback(query, "ユーザー情報を確認できませんでした。", show_alert=True)
        return
    await state.clear()
    set_user_mode(user_id, "status")
    mark_user_active(user_id)
    now = utcnow()
    user = get_user_with_default(user_id) or ensure_user(user_id, now=now)
    formatted = format_status(user, now=now)
    if query.message:
        await query.message.answer(formatted, reply_markup=base_menu_kb())
    else:
        await bot.send_message(user_id, formatted, reply_markup=base_menu_kb())


@dp.callback_query(F.data == "nav:charge")
async def handle_nav_charge(query: CallbackQuery, state: FSMContext) -> None:
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    if user_id is not None:
        ensure_user(user_id)
        set_user_mode(user_id, "charge")
        mark_user_active(user_id)
    await state.clear()
    if query.message:
        await prompt_charge_menu(query.message)
    elif user_id is not None:
        await bot.send_message(user_id, CHARGE_MODE_PROMPT, reply_markup=base_menu_kb())
        await bot.send_message(user_id, get_store_intro_text(), reply_markup=build_store_keyboard())


@dp.callback_query(F.data.startswith("buy:"))
async def handle_buy_callback(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    data = query.data or ""
    sku = data.split(":", maxsplit=1)[1] if ":" in data else None
    product = get_product(sku) if sku else None
    if not product:
        await _safe_answer_callback(
            query, "商品情報を取得できませんでした。少し時間をおいてお試しください。", show_alert=True
        )
        return

    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await _safe_answer_callback(
            query, "ユーザーを特定できませんでした。個別チャットからお試しください。", show_alert=True
        )
        return

    now = utcnow()
    user = ensure_user(user_id, now=now)
    _safe_log_payment_event(
        user_id=user_id, event_type="buy_click", sku=product.sku, payload=query.data
    )
    if product.sku == "ADDON_IMAGES" and not IMAGE_ADDON_ENABLED:
        await _safe_answer_callback(
            query, "画像追加オプションは準備中です。リリースまでお待ちください。", show_alert=True
        )
        return
    if not has_accepted_terms(user_id):
        await _safe_answer_callback(query, TERMS_PROMPT_BEFORE_BUY, show_alert=True)
        if query.message:
            await query.message.answer(
                f"{TERMS_PROMPT_BEFORE_BUY}\n/terms から同意をお願いします。",
                reply_markup=build_terms_prompt_keyboard(),
            )
        return

    if product.sku == "TICKET_3":
        has_pass = effective_has_pass(user_id, user, now=now)
        if has_pass:
            await _safe_answer_callback(
                query,
                "パスが有効なため、3枚スプレッドは追加購入なしでお使いいただけます。",
                show_alert=True,
            )
            if query.message:
                await query.message.answer(
                    "パスが有効なので、追加のスリーカード購入は不要です。🎩占いから3枚スプレッドをお試しください。",
                    reply_markup=base_menu_kb(),
                )
            return

    if _check_purchase_dedup(user_id, product.sku):
        _safe_log_payment_event(
            user_id=user_id, event_type="buy_dedup_hit", sku=product.sku, payload=query.data
        )
        await _safe_answer_callback(
            query,
            "購入画面は既に表示しています。開いている決済画面をご確認ください。",
            show_alert=True,
        )
        if query.message:
            await query.message.answer(
                "同じ商品への購入確認を進行中です。開いている購入画面を確認してください。",
                reply_markup=base_menu_kb(),
            )
        return
    payload = json.dumps({"sku": product.sku, "user_id": user_id})
    prices = [LabeledPrice(label=product.title, amount=product.price_stars)]

    if query.message:
        try:
            await query.message.answer_invoice(
                title=product.title,
                description=product.description,
                payload=payload,
                provider_token="",
                currency="XTR",
                prices=prices,
            )
        except TelegramBadRequest as exc:
            if _is_stale_query_error(exc):
                await _handle_stale_interaction(
                    query, user_id=user_id, sku=product.sku, payload=query.data
                )
                return
            logger.exception(
                "Failed to send invoice",
                extra={"user_id": user_id, "sku": product.sku, "error": str(exc)},
            )
            await query.message.answer(
                "決済画面の表示に失敗しました。/buy からもう一度お試しください。",
                reply_markup=_build_charge_retry_keyboard(),
            )
            return
    await _safe_answer_callback(query, "お支払い画面を開きます。ゆっくり進めてくださいね。")


@dp.callback_query(F.data == "addon:pending")
async def handle_addon_pending(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    await _safe_answer_callback(query, "画像追加オプションは準備中です。もう少しお待ちください。", show_alert=True)


@dp.callback_query(F.data.startswith("tarot_theme:"))
async def handle_tarot_theme_select(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    data = query.data or ""
    _, _, theme = data.partition(":")
    user_id = query.from_user.id if query.from_user else None
    mark_user_active(user_id)
    if theme not in {"love", "marriage", "work", "life"}:
        await _safe_answer_callback(query, "テーマを認識できませんでした。", show_alert=True)
        return

    set_user_mode(user_id, "tarot")
    set_tarot_theme(user_id, theme)
    set_tarot_flow(user_id, "awaiting_question")
    await _safe_answer_callback(query, "テーマを設定しました。")
    if query.message:
        prompt_text = build_tarot_question_prompt(theme)
        await query.message.edit_text(prompt_text)
    elif user_id is not None:
        await bot.send_message(user_id, build_tarot_question_prompt(theme))


@dp.callback_query(F.data == "upgrade_to_three")
async def handle_upgrade_to_three(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    if query.message:
        await query.message.answer(
            "3枚スプレッドで深掘りするには /buy からチケットを購入してください。\n"
            "決済が未開放の場合は少しお待ちください。",
            reply_markup=build_store_keyboard(),
        )


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    sku, payload_user_id = _parse_invoice_payload(pre_checkout_query.invoice_payload or "")
    product = get_product(sku) if sku else None
    user_id = pre_checkout_query.from_user.id if pre_checkout_query.from_user else None
    log_user_id = user_id or payload_user_id
    if not product:
        _safe_log_payment_event(
            user_id=log_user_id,
            event_type="pre_checkout_invalid_product",
            sku=sku if sku else None,
            payload=pre_checkout_query.invoice_payload,
        )
        logger.warning(
            "Pre-checkout received without product",
            extra={"payload": pre_checkout_query.invoice_payload},
        )
        await _safe_answer_pre_checkout(
            pre_checkout_query,
            ok=False,
            error_message="商品情報を確認できませんでした。最初からお試しください。",
        )
        return
    if payload_user_id is None or user_id is None or payload_user_id != user_id:
        _safe_log_payment_event(
            user_id=log_user_id,
            event_type="pre_checkout_rejected",
            sku=product.sku,
            payload=pre_checkout_query.invoice_payload,
        )
        await _safe_answer_pre_checkout(
            pre_checkout_query,
            ok=False,
            error_message="購入者情報を確認できませんでした。もう一度お試しください。",
        )
        return

    ensure_user(user_id)
    _safe_log_payment_event(
        user_id=user_id,
        event_type="pre_checkout",
        sku=product.sku,
        payload=pre_checkout_query.invoice_payload,
    )
    await _safe_answer_pre_checkout(pre_checkout_query, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    sku, payload_user_id = _parse_invoice_payload(payment.invoice_payload or "")
    product = get_product(sku) if sku else None
    user_id_message = message.from_user.id if message.from_user else None
    user_id = payload_user_id if payload_user_id is not None else user_id_message
    if user_id_message is not None and user_id is not None and user_id != user_id_message:
        await message.answer(
            "お支払い情報の確認に失敗しました。サポートまでお問い合わせください。\n"
            "処理は完了している場合がありますので、ご安心ください。"
        )
        return

    if not product or user_id is None:
        await message.answer(
            "お支払いは完了しましたが、購入情報の確認に少し時間がかかっています。\n"
            "お手数ですがサポートまでお問い合わせください。"
        )
        return

    ensure_user(user_id)
    payment_record, created = log_payment(
        user_id=user_id,
        sku=product.sku,
        stars=payment.total_amount,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id,
    )
    _safe_log_payment_event(
        user_id=user_id,
        event_type="successful_payment" if created else "successful_payment_duplicate",
        sku=product.sku,
        payload=payment.telegram_payment_charge_id,
    )
    if not created:
        await message.answer(
            "このお支払いはすでに処理済みです。/status から利用状況をご確認ください。",
            reply_markup=build_purchase_followup_keyboard(),
        )
        return
    updated_user = grant_purchase(user_id, product.sku)
    unlock_message = build_unlock_text(product, updated_user)
    thank_you_lines = [
        f"{product.title}のご購入ありがとうございました！",
        unlock_message,
        "付与内容は /status でも確認できます。",
        "下のボタンから占いに戻るか、ステータスを確認してください。",
    ]
    await message.answer("\n".join(thank_you_lines), reply_markup=build_purchase_followup_keyboard())


def _build_admin_grant_summary(user: UserRecord, product: Product, now: datetime) -> str:
    pass_until = effective_pass_expires_at(user.user_id, user, now)
    if pass_until:
        pass_label = pass_until.astimezone(USAGE_TIMEZONE).strftime("%Y-%m-%d %H:%M JST")
    else:
        pass_label = "なし"
    ticket_line = f"3枚={user.tickets_3} / 7枚={user.tickets_7} / 10枚={user.tickets_10}"
    lines = [
        f"付与が完了しました。{product.title}（SKU: {product.sku}）",
        f"対象ユーザーID: {user.user_id}",
        f"・パス有効期限: {pass_label}",
        f"・チケット残数: {ticket_line}",
        f"・画像オプション: {'有効' if user.images_enabled else '無効'}",
        "ユーザーには /status のご案内をお願いします。迷子になった場合は /menu から戻れます。",
    ]
    return "\n".join(lines)


def _build_admin_revoke_summary(user: UserRecord, product: Product, now: datetime) -> str:
    pass_until = effective_pass_expires_at(user.user_id, user, now)
    pass_label = (
        pass_until.astimezone(USAGE_TIMEZONE).strftime("%Y-%m-%d %H:%M JST")
        if pass_until
        else "なし"
    )
    ticket_line = f"3枚={user.tickets_3} / 7枚={user.tickets_7} / 10枚={user.tickets_10}"
    lines = [
        f"権限の取り消しが完了しました。{product.title}（SKU: {product.sku}）",
        f"対象ユーザーID: {user.user_id}",
        f"・パス有効期限: {pass_label}",
        f"・チケット残数: {ticket_line}",
        f"・画像オプション: {'有効' if user.images_enabled else '無効'}",
        "ご不便をおかけしますが、ユーザーには /status で状況確認を促してください。",
    ]
    return "\n".join(lines)


@dp.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    admin_id = message.from_user.id if message.from_user else None
    if not is_admin_user(admin_id):
        await message.answer("このコマンドは管理者専用です。")
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        valid_skus = ", ".join(product.sku for product in iter_products())
        await message.answer(
            "管理者メニューです。サポート中のサブコマンド:\n"
            "・/admin grant <user_id> <SKU> : 指定ユーザーに付与します。\n"
            "・/admin revoke <user_id> <SKU> : 指定ユーザーの権限を剥奪します。\n"
            f"SKU候補: {valid_skus}"
        )
        return

    subcommand = parts[1].lower()
    if subcommand not in {"grant", "revoke"}:
        await message.answer(
            "現在サポートしているのは grant / revoke です。/admin grant または /admin revoke をご利用ください。"
        )
        return

    if len(parts) < 4:
        valid_skus = ", ".join(product.sku for product in iter_products())
        await message.answer(
            "使い方:\n"
            "・付与: /admin grant <user_id> <SKU>\n"
            "・剥奪: /admin revoke <user_id> <SKU>\n"
            "例: /admin grant 123456789 PASS_7D\n"
            f"SKU候補: {valid_skus}"
        )
        return

    target_raw = parts[2].strip()
    try:
        target_user_id = int(target_raw)
    except ValueError:
        await message.answer("ユーザーIDは数字でご指定ください。")
        return

    sku = parts[3].strip().upper()
    product = get_product(sku)
    if not product:
        valid_skus = ", ".join(prod.sku for prod in iter_products())
        await message.answer(f"SKUが認識できませんでした。利用可能なSKU: {valid_skus}")
        return

    if subcommand == "grant":
        try:
            ensure_user(target_user_id)
            updated_user = grant_purchase(target_user_id, product.sku, now=utcnow())
            _safe_log_payment_event(
                user_id=target_user_id,
                event_type="admin_grant",
                sku=product.sku,
                payload=message.text,
            )
        except Exception:
            logger.exception(
                "Failed to grant purchase via admin",
                extra={"admin_id": admin_id, "target_user_id": target_user_id, "sku": sku},
            )
            _safe_log_audit(
                action="admin_grant",
                actor_user_id=admin_id,
                target_user_id=target_user_id,
                payload=message.text,
                status="failed",
            )
            await message.answer("恐れ入ります、付与処理でエラーが発生しました。ログをご確認ください。")
            return

        summary = _build_admin_grant_summary(updated_user, product, utcnow())
        _safe_log_audit(
            action="admin_grant",
            actor_user_id=admin_id,
            target_user_id=target_user_id,
            payload=message.text,
            status="success",
        )
        await message.answer(summary)
        return

    existing_user = get_user(target_user_id)
    if not existing_user:
        await message.answer(
            "まだ登録履歴が見つかりませんでした。ユーザーが一度も利用していない可能性があります。"
        )
        return

    try:
        updated_user = revoke_purchase(target_user_id, product.sku, now=utcnow())
        _safe_log_payment_event(
            user_id=target_user_id,
            event_type="admin_revoke",
            sku=product.sku,
            payload=message.text,
        )
    except Exception:
        logger.exception(
            "Failed to revoke purchase via admin",
            extra={"admin_id": admin_id, "target_user_id": target_user_id, "sku": sku},
        )
        _safe_log_audit(
            action="admin_revoke",
            actor_user_id=admin_id,
            target_user_id=target_user_id,
            payload=message.text,
            status="failed",
        )
        await message.answer("恐れ入ります、取り消し処理でエラーが発生しました。ログをご確認ください。")
        return

    summary = _build_admin_revoke_summary(updated_user, product, utcnow())
    _safe_log_audit(
        action="admin_revoke",
        actor_user_id=admin_id,
        target_user_id=target_user_id,
        payload=message.text,
        status="success",
    )
    await message.answer(summary)


@dp.message(Command("refund"))
async def cmd_refund(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if not is_admin_user(user_id):
        await message.answer("このコマンドは管理者専用です。")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer("使い方: /refund <telegram_payment_charge_id>")
        return

    charge_id = parts[1].strip()
    payment = get_payment_by_charge_id(charge_id)
    if not payment:
        await message.answer("指定の決済が見つかりませんでした。IDをご確認ください。")
        return

    try:
        await bot.refund_star_payment(
            user_id=payment.user_id,
            telegram_payment_charge_id=charge_id,
        )
    except Exception:
        logger.exception("Failed to refund payment %s", charge_id)
        await message.answer("返金処理に失敗しました。ログを確認してください。")
        return

    updated = mark_payment_refunded(charge_id)
    _safe_log_payment_event(
        user_id=payment.user_id,
        event_type="refund",
        sku=payment.sku,
        payload=charge_id,
    )
    status_line = f"status={updated.status}" if updated else "status=refunded"
    await message.answer(
        "返金処理が完了しました。\n"
        f"ユーザーID: {payment.user_id}\n"
        f"SKU: {payment.sku}\n"
        f"決済ID: {charge_id}\n"
        f"{status_line}"
    )


async def handle_tarot_reading(
    message: Message,
    user_query: str,
    *,
    spread: Spread | None = None,
    guidance_note: str | None = None,
    short_response: bool = False,
    theme: str | None = None,
) -> None:
    total_start = perf_counter()
    openai_latency_ms: float | None = None
    user_id = message.from_user.id if message.from_user else None
    chat_id = get_chat_id(message)
    can_use_bot = hasattr(message, "chat") and getattr(message.chat, "id", None) is not None
    release_inflight = await _acquire_inflight(user_id, message)

    spread_to_use = spread or choose_spread(user_query)
    effective_theme = theme or get_tarot_theme(user_id)
    rng = random.Random()
    drawn = draw_cards(spread_to_use, rng=rng)

    drawn_payload: list[dict[str, str]] = []
    position_lookup = {pos.id: pos for pos in spread_to_use.positions}
    for item in drawn:
        position = position_lookup[item.position_id]
        keywords = (
            item.card.keywords_reversed_ja
            if item.is_reversed
            else item.card.keywords_upright_ja
        )
        drawn_payload.append(
            {
                "id": position.id,
                "label_ja": position.label_ja,
                "meaning_ja": position.meaning_ja,
                "card": {
                    "id": item.card.id,
                    "name_ja": item.card.name_ja,
                    "name_en": item.card.name_en,
                    "orientation": "reversed" if item.is_reversed else "upright",
                    "orientation_label_ja": orientation_label(item.is_reversed),
                    "keywords_ja": list(keywords),
                },
            }
        )

    action_count = determine_action_count(user_id, getattr(message, "message_id", None))
    messages = build_tarot_messages(
        spread=spread_to_use,
        user_query=user_query,
        drawn_cards=drawn_payload,
        short=short_response,
        theme=effective_theme,
        action_count=action_count,
    )

    status_message: Message | None = None
    try:
        status_message = await message.answer(
            "🔮鑑定中です…（しばらくお待ちください）",
            reply_markup=ensure_quick_menu(),
        )
        openai_start = perf_counter()
        answer, fatal = await call_openai_with_retry(messages)
        openai_latency_ms = (perf_counter() - openai_start) * 1000
        if fatal:
            error_text = (
                answer
                + "\n\nご不便をおかけしてごめんなさい。時間をおいて再度お試しください。"
            )
            if can_use_bot and chat_id is not None:
                await send_long_text(
                    chat_id,
                    error_text,
                    reply_to=getattr(message, "message_id", None),
                    edit_target=status_message,
                )
            else:
                await message.answer(error_text)
            return

        if spread_to_use.id == THREE_CARD_TIME_AXIS.id:
            base_answer = answer
            if guidance_note:
                base_answer = f"{base_answer}\n\n{guidance_note}"
            base_answer = append_caution_note(user_query, base_answer)
            formatted_answer = format_time_axis_tarot_answer(
                base_answer,
                drawn_cards=drawn_payload,
                time_range_text="前後3か月",
                caution_note=CAUTION_NOTE,
            )
        else:
            formatted_answer = format_long_answer(
                answer,
                "tarot",
                card_line=format_drawn_cards(drawn_payload),
                position_labels=spread_to_use.position_labels,
            )
            if guidance_note:
                formatted_answer = f"{formatted_answer}\n\n{guidance_note}"
            formatted_answer = append_caution_note(user_query, formatted_answer)
            formatted_answer = finalize_tarot_answer(
                formatted_answer,
                card_line_prefix=CARD_LINE_PREFIX,
                caution_note=CAUTION_NOTE,
            )
        bullet_count = sum(
            1 for line in formatted_answer.splitlines() if line.lstrip().startswith("・")
        )
        logger.info(
            "Tarot bullet count",
            extra={
                "action_count": action_count,
                "bullet_count": bullet_count,
            },
        )
        upgrade_markup = build_upgrade_keyboard() if spread_to_use.id == ONE_CARD.id else None
        if can_use_bot and chat_id is not None:
            await send_long_text(
                chat_id,
                formatted_answer,
                reply_to=getattr(message, "message_id", None),
                edit_target=status_message,
                reply_markup_last=upgrade_markup,
            )
        else:
            await message.answer(formatted_answer, reply_markup=upgrade_markup)
    except Exception:
        logger.exception("Unexpected error during tarot reading")
        fallback = (
            "占いの準備で少しつまずいてしまいました。\n"
            "時間をおいて、もう一度話しかけてもらえるとうれしいです。"
        )
        if status_message and can_use_bot and chat_id is not None:
            await send_long_text(
                chat_id,
                fallback,
                reply_to=getattr(message, "message_id", None),
                edit_target=status_message,
            )
        else:
            await message.answer(fallback)
    finally:
        total_ms = (perf_counter() - total_start) * 1000
        logger.info(
            "Tarot handler finished",
            extra={
                "mode": "tarot",
                "user_id": user_id,
                "message_id": getattr(message, "message_id", None),
                "tarot_theme": effective_theme,
                "openai_latency_ms": round(openai_latency_ms or 0, 2),
                "total_handler_ms": round(total_ms, 2),
            },
        )
        release_inflight()


def _is_consult_intent(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith(("相談:", "相談：")):
        return True

    lowered = stripped.lower()
    consult_keywords = [
        "悩み",
        "相談",
        "不安",
        "辛い",
        "つらい",
        "どうすれば",
        "復縁",
        "別れ",
        "仕事",
        "人間関係",
        "お金",
    ]
    return any(keyword in lowered for keyword in consult_keywords)


def _should_show_general_chat_full_notice(user: UserRecord, now: datetime) -> bool:
    if not user.last_general_chat_block_notice_at:
        return True
    return (now - user.last_general_chat_block_notice_at) >= GENERAL_CHAT_BLOCK_NOTICE_COOLDOWN


def _build_consult_block_message(*, trial_active: bool, short: bool = False) -> str:
    if trial_active:
        if short:
            return "ご相談は本日の無料枠を使い切りました。パスは /buy からご利用いただけます。"
        return (
            "trial中の相談チャット無料枠（1日2通）は本日分を使い切りました。\n"
            "/buy から7日/30日パスを購入すると回数無制限でご利用いただけます。"
        )
    if short:
        return "相談チャットはパス専用です。/buy からご検討ください。"
    return "6日目以降の相談チャットはパス専用です。/buy から7日または30日のパスをご検討ください。"


async def handle_general_chat(message: Message, user_query: str) -> None:
    now = utcnow()
    user_id = message.from_user.id if message.from_user else None
    total_start = perf_counter()
    openai_latency_ms: float | None = None
    consult_intent = _is_consult_intent(user_query)
    admin_mode = is_admin_user(user_id)
    chat_id_value = getattr(getattr(message, "chat", None), "id", None)
    can_use_bot = chat_id_value is not None
    user: UserRecord | None = ensure_user(user_id, now=now) if user_id is not None else None
    paywall_triggered = False

    if await respond_with_safety_notice(message, user_query):
        logger.info(
            "Safety notice triggered",
            extra={
                "mode": "chat",
                "user_id": user_id,
                "text_preview": _preview_text(user_query),
                "tarot_flow": TAROT_FLOW.get(user_id),
                "tarot_theme": get_tarot_theme(user_id),
                "route": "consult_safety",
                "paywall_triggered": paywall_triggered,
            },
        )
        return

    if user is not None:
        trial_active = _is_in_general_chat_trial(user, now)
        out_of_quota = user.general_chat_count_today >= FREE_GENERAL_CHAT_PER_DAY
        has_pass = effective_has_pass(user_id, user, now=now)

        if (trial_active and out_of_quota and not has_pass) or (
            not trial_active and not has_pass
        ):
            paywall_triggered = True
            if not consult_intent:
                await message.answer(NON_CONSULT_OUT_OF_QUOTA_MESSAGE)
                return

            full_notice = _should_show_general_chat_full_notice(user, now)
            block_message = _build_consult_block_message(
                trial_active=trial_active, short=not full_notice
            )
            reply_markup = build_store_keyboard() if full_notice else None
            await message.answer(block_message, reply_markup=reply_markup)
            if full_notice and user_id is not None:
                set_last_general_chat_block_notice(user_id, now=now)
            return

        if not admin_mode:
            increment_general_chat_count(user_id, now=now)

    logger.info(
        "Handling message",
        extra={
            "mode": "chat",
            "user_id": message.from_user.id if message.from_user else None,
            "admin_mode": admin_mode,
            "text_preview": _preview_text(user_query),
            "route": "consult",
            "tarot_flow": TAROT_FLOW.get(user_id),
            "tarot_theme": get_tarot_theme(user_id),
            "paywall_triggered": paywall_triggered,
        },
    )

    release_inflight = await _acquire_inflight(
        user_id, message, busy_message="いま返信中です…少し待ってね。"
    )

    try:
        openai_start = perf_counter()
        answer, fatal = await call_openai_with_retry(build_general_chat_messages(user_query))
        openai_latency_ms = (perf_counter() - openai_start) * 1000
        if fatal:
            error_text = (
                answer
                + "\n\nご不便をおかけしてごめんなさい。時間をおいて再度お試しください。"
            )
            if can_use_bot and chat_id_value is not None:
                await send_long_text(
                    chat_id_value, error_text, reply_to=message.message_id
                )
            else:
                await message.answer(error_text)
            return
        safe_answer = await ensure_general_chat_safety(answer)
        safe_answer = format_long_answer(safe_answer, "consult")
        safe_answer = append_caution_note(user_query, safe_answer)
        if can_use_bot and chat_id_value is not None:
            await send_long_text(
                chat_id_value,
                safe_answer,
                reply_to=message.message_id,
            )
        else:
            await message.answer(safe_answer)
    except Exception:
        logger.exception("Unexpected error during general chat")
        fallback = (
            "すみません、今ちょっと調子が悪いみたいです…\n"
            "少し時間をおいてから、もう一度メッセージを送ってもらえると助かります。"
        )
        await message.answer(fallback)
    finally:
        total_ms = (perf_counter() - total_start) * 1000
        logger.info(
            "Consult handler finished",
            extra={
                "mode": "chat",
                "user_id": user_id,
                "message_id": getattr(message, "message_id", None),
                "openai_latency_ms": round(openai_latency_ms or 0, 2),
                "total_handler_ms": round(total_ms, 2),
            },
        )
        release_inflight()


# Catch-all handler for non-command text messages
@dp.message(
    ~Command(
        commands=[
            "terms",
            "support",
            "paysupport",
            "buy",
            "status",
            "read1",
            "love1",
            "refund",
            "start",
            "help",
        ]
    )
)
async def handle_message(message: Message) -> None:
    content_type = getattr(message, "content_type", ContentType.TEXT)
    is_text = content_type == ContentType.TEXT
    if not is_text:
        ok, error_message = validate_question_text(None, is_text=False)
        if not ok and error_message:
            await message.answer(error_message, reply_markup=base_menu_kb())
        return

    text = (message.text or "").strip()
    now = utcnow()
    user_id = message.from_user.id if message.from_user else None
    if not _mark_recent_handled(message):
        return
    if await reset_state_if_inactive(message, now=now):
        return
    mark_user_active(user_id, now=now)
    admin_mode = is_admin_user(user_id)
    user_mode = get_user_mode(user_id)
    tarot_flow = TAROT_FLOW.get(user_id)
    tarot_theme = get_tarot_theme(user_id)

    logger.info(
        "Received message",
        extra={
            "mode": "router",
            "user_id": user_id,
            "admin_mode": admin_mode,
            "text_preview": _preview_text(text),
            "tarot_flow": tarot_flow,
            "tarot_theme": tarot_theme,
            "route": "received",
            "paywall_triggered": False,
        },
    )

    if not text:
        await message.answer(
            "気になることをもう少し詳しく教えてくれるとうれしいです。",
            reply_markup=base_menu_kb(),
        )
        return

    if text == "🎩占い":
        await prompt_tarot_mode(message)
        return

    if text == "💬相談":
        await prompt_consult_mode(message)
        return

    if text == "🛒チャージ":
        await prompt_charge_menu(message)
        return

    if text == "📊ステータス":
        await prompt_status(message, now=now)
        return

    spread_from_command, cleaned = parse_spread_command(text)

    if spread_from_command:
        set_user_mode(user_id, "tarot")
        if text.lower().startswith("/love1"):
            set_tarot_theme(user_id, "love")
        user_query = cleaned or "今気になっていることについて占ってください。"
        await execute_tarot_request(
            message,
            user_query=user_query,
            spread=spread_from_command,
            theme=get_tarot_theme(user_id),
        )
        return

    if tarot_flow == "awaiting_theme":
        await message.answer(
            TAROT_THEME_PROMPT, reply_markup=build_tarot_theme_keyboard()
        )
        return

    if tarot_flow == "awaiting_question":
        ok, error_message = validate_question_text(text, is_text=is_text)
        if not ok and error_message:
            await message.answer(error_message, reply_markup=ensure_quick_menu())
            return
        set_tarot_flow(user_id, None)
        await execute_tarot_request(
            message,
            user_query=text,
            spread=ONE_CARD,
            theme=tarot_theme,
        )
        return

    if user_mode == "tarot" or is_tarot_request(text):
        ok, error_message = validate_question_text(text, is_text=is_text)
        if not ok and error_message:
            await message.answer(error_message, reply_markup=ensure_quick_menu())
            return
        set_user_mode(user_id, "tarot")
        await execute_tarot_request(
            message,
            user_query=text,
            spread=ONE_CARD,
            theme=tarot_theme,
        )
        return

    ok, error_message = validate_question_text(text, is_text=is_text)
    if not ok and error_message:
        await message.answer(error_message, reply_markup=ensure_quick_menu())
        return

    await handle_general_chat(message, user_query=text)

async def main() -> None:
    setup_logging()
    db_ok, db_messages = check_db_health()
    for message in db_messages:
        logger.info("DB health check: %s", message, extra={"mode": "startup"})
    if not db_ok:
        logger.error("DB health check failed; exiting for safety.")
        raise SystemExit(1)
    logger.info(
        "Starting akolasia_tarot_bot",
        extra={
            "mode": "startup",
            "admin_ids_count": len(ADMIN_USER_IDS),
            "paywall_enabled": PAYWALL_ENABLED,
            "polling": True,
        },
    )
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
