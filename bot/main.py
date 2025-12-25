import asyncio
import json
import logging
import os
import random
import re
import unicodedata
from collections import deque
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
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
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from bot.keyboards.common import base_menu_kb
from bot.middlewares.throttle import ThrottleMiddleware
from bot.utils.postprocess import postprocess_llm_text
from bot.utils.replies import ensure_quick_menu
from bot.utils.tarot_output import finalize_tarot_answer, format_time_axis_tarot_answer
from bot.utils.validators import validate_question_text
from bot.texts.i18n import normalize_lang, t
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
    get_daily_stats,
    get_latest_payment,
    get_payment_by_charge_id,
    get_recent_feedback,
    get_user,
    get_user_lang,
    grant_purchase,
    has_accepted_terms,
    increment_general_chat_count,
    increment_one_oracle_count,
    log_audit,
    log_app_event,
    log_feedback,
    log_payment,
    log_payment_event,
    mark_payment_refunded,
    set_user_lang,
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
    get_consult_system_prompt,
    get_tarot_fixed_output_format,
    get_tarot_output_rules,
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
    orientation_label_by_lang,
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
GENERAL_CHAT_BLOCK_NOTICE_COOLDOWN = timedelta(hours=1)
PURCHASE_DEDUP_TTL_SECONDS = 30.0
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
TAROT_THEME_LABELS_EN: dict[str, str] = {
    "love": "Love",
    "marriage": "Marriage",
    "work": "Work",
    "life": "Life",
}
TAROT_THEME_LABELS_PT: dict[str, str] = {
    "love": "Amor",
    "marriage": "Casamento",
    "work": "Trabalho",
    "life": "Vida",
}
TAROT_THEME_EXAMPLES_EN: dict[str, tuple[str, ...]] = {
    "love": (
        "How does my crush feel?",
        "When will they reach out?",
        "How can we get closer?",
        "Is reconciliation possible?",
    ),
    "marriage": (
        "When is the right time to marry?",
        "Can I marry this person?",
        "Will the proposal go well?",
        "When should I tell my family?",
    ),
    "work": (
        "How can I be recognized at work?",
        "Should I change jobs?",
        "How will my work go this month?",
        "Will workplace relationships improve?",
    ),
    "life": (
        "How will this year flow?",
        "What should I focus on most now?",
        "Which option is better for my choice?",
        "Will my finances stabilize?",
    ),
}
TAROT_THEME_EXAMPLES_PT: dict[str, tuple[str, ...]] = {
    "love": (
        "O que a pessoa amada sente?",
        "Quando vou receber uma mensagem?",
        "Como posso nos aproximar?",
        "Há chance de reconciliação?",
    ),
    "marriage": (
        "Qual o momento certo para casar?",
        "Vou me casar com essa pessoa?",
        "O pedido vai dar certo?",
        "Quando contar para a família?",
    ),
    "work": (
        "Como posso ser reconhecido no trabalho?",
        "Devo trocar de emprego?",
        "Como vai ser meu trabalho neste mês?",
        "Os relacionamentos no trabalho vão melhorar?",
    ),
    "life": (
        "Como será o fluxo deste ano?",
        "No que devo focar mais agora?",
        "Qual opção é melhor para minha escolha?",
        "Minhas finanças vão estabilizar?",
    ),
}
POSITION_LABELS_I18N: dict[str, dict[str, str]] = {
    "main": {"en": "Main message", "pt": "Mensagem principal"},
    "past": {"en": "Past", "pt": "Passado"},
    "present": {"en": "Present", "pt": "Presente"},
    "future": {"en": "Future", "pt": "Futuro"},
    "your_feelings": {"en": "Your feelings", "pt": "Seus sentimentos"},
    "partner_feelings": {"en": "Partner's feelings", "pt": "Sentimentos da outra pessoa"},
    "current_situation": {"en": "Current situation", "pt": "Situação atual"},
    "obstacle": {"en": "Obstacle", "pt": "Obstáculo"},
    "near_future": {"en": "Near future", "pt": "Futuro próximo"},
    "advice": {"en": "Advice", "pt": "Conselho"},
    "outcome": {"en": "Outcome", "pt": "Resultado"},
    "challenge": {"en": "Challenge", "pt": "Desafio"},
    "conscious": {"en": "Conscious motives", "pt": "Motivações conscientes"},
    "subconscious": {"en": "Subconscious", "pt": "Subconsciente"},
    "self_position": {"en": "Advice (your stance)", "pt": "Conselho (sua postura)"},
    "environment": {"en": "Environment", "pt": "Ambiente"},
    "hopes_fears": {"en": "Hopes / Fears", "pt": "Esperanças / medos"},
}
POSITION_MEANINGS_I18N: dict[str, dict[str, str]] = {
    "main": {"en": "Main message for you.", "pt": "Mensagem principal para você."},
    "past": {"en": "How past events or feelings shape the present.", "pt": "Como o passado influencia o presente."},
    "present": {"en": "Clarifies current hesitation, stagnation, or crossroads.", "pt": "Organiza dúvidas ou travas do momento."},
    "future": {
        "en": "Upcoming flow, possibilities, and cautions, including hints for past/present.",
        "pt": "Fluxo futuro, possibilidades e cuidados, incluindo alertas sobre passado/presente.",
    },
    "your_feelings": {"en": "Your true feelings and emotional flow.", "pt": "Seus sentimentos verdadeiros e o fluxo deles."},
    "partner_feelings": {"en": "The other person's honest feelings toward you.", "pt": "O que a outra pessoa sente por você."},
    "current_situation": {"en": "The current relationship status and atmosphere around you two.", "pt": "O estado atual e o clima ao redor de vocês."},
    "obstacle": {"en": "Causes of distance, friction, or obstacles.", "pt": "Causas de distância, atrito ou obstáculos."},
    "near_future": {"en": "Near-term flow and signs of change.", "pt": "Fluxo de curto prazo e sinais de mudança."},
    "advice": {"en": "Actions or mindset you can take for a better future.", "pt": "Ações ou posturas que você pode tomar para melhorar."},
    "outcome": {"en": "Likely result or landing point if the current flow continues.", "pt": "Resultado provável se o fluxo atual continuar."},
    "challenge": {"en": "Obstacle or issue to overcome.", "pt": "Obstáculo ou questão a superar."},
    "conscious": {"en": "What you are aware of—recognized aims or wishes.", "pt": "O que você percebe: objetivos ou desejos conscientes."},
    "subconscious": {"en": "Unseen motives or deeper desires.", "pt": "Motivações ocultas ou desejos mais profundos."},
    "self_position": {"en": "Your stance or role and how to engage.", "pt": "Sua postura ou papel e como agir."},
    "environment": {"en": "Influences and support/constraints around you.", "pt": "Influências e apoios/limitações ao redor."},
    "hopes_fears": {"en": "Hopes and what you wish to avoid.", "pt": "Esperanças e o que deseja evitar."},
}


def _get_position_label_translation(position_id: str, lang: str) -> str | None:
    lang_code = normalize_lang(lang)
    return (POSITION_LABELS_I18N.get(position_id) or {}).get(lang_code)


def _get_position_meaning_translation(position_id: str, lang: str) -> str | None:
    lang_code = normalize_lang(lang)
    return (POSITION_MEANINGS_I18N.get(position_id) or {}).get(lang_code)
CAUTION_NOTE = (
    "※医療・法律・投資の判断は専門家にご相談ください（一般的な情報としてお伝えします）。"
)
CAUTION_NOTES = {
    "ja": CAUTION_NOTE,
    "en": "※ For medical, legal, or investment decisions, please consult professionals (general information only).",
    "pt": "※ Para decisões médicas, jurídicas ou de investimento, consulte profissionais (informação geral).",
}
TIME_RANGE_TEXTS = {
    "ja": "前後3か月",
    "en": "3 months",
    "pt": "3 meses",
}
REWRITE_PROMPTS = {
    "ja": (
        "次の文章から、タロット・カード・占いに関する言及をすべて取り除いて日本語で書き直してください。"
        "丁寧で落ち着いた敬語を維持し、相談の意図や励ましは残してください。"
    ),
    "en": (
        "Rewrite the text in English, removing any mention of tarot, cards, or divination."
        " Keep a calm, supportive tone and preserve the intent of the consultation."
    ),
    "pt": (
        "Reescreva o texto em português, removendo qualquer menção a tarô, cartas ou adivinhação."
        " Mantenha um tom calmo e acolhedor e preserve a intenção da conversa."
    ),
}
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
SUPPORTED_LANGS = {"ja", "en", "pt"}
LANGUAGE_BUTTON_LABELS = {
    lang: t(lang, "MENU_LANGUAGE_LABEL") for lang in SUPPORTED_LANGS
}
GLOBE_EMOJI_PREFIXES = ("🌐", "🌍", "🌎", "🌏")
_VARIATION_SELECTOR_RE = re.compile(r"[\ufe00-\ufe0f\U000e0100-\U000e01ef]")


def _get_theme_labels(lang: str) -> dict[str, str]:
    if lang == "en":
        return TAROT_THEME_LABELS_EN
    if lang == "pt":
        return TAROT_THEME_LABELS_PT
    return TAROT_THEME_LABELS


def _get_theme_examples(lang: str) -> dict[str, tuple[str, ...]]:
    if lang == "en":
        return TAROT_THEME_EXAMPLES_EN
    if lang == "pt":
        return TAROT_THEME_EXAMPLES_PT
    return TAROT_THEME_EXAMPLES


def format_theme_examples_for_help(lang: str = "ja") -> str:
    lang_code = normalize_lang(lang)
    theme_labels = _get_theme_labels(lang_code)
    theme_examples = _get_theme_examples(lang_code)
    bullet = "・" if lang_code == "ja" else "•"
    bullet_prefix = bullet if lang_code == "ja" else f"{bullet} "
    lines: list[str] = []
    for theme in TAROT_THEME_LABELS:
        examples = theme_examples.get(theme)
        if not examples:
            continue

        lines.append(theme_labels.get(theme, TAROT_THEME_LABELS[theme]))
        for example in examples:
            lines.append(f"{bullet_prefix}{example}")
        lines.append("")

    if lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def build_help_text(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    if lang_code == "ja":
        return HELP_TEXT_TEMPLATE.format(theme_examples=format_theme_examples_for_help(lang_code))
    template = t(lang_code, "HELP_TEXT_TEMPLATE")
    return template.format(theme_examples=format_theme_examples_for_help(lang_code))


def build_tarot_question_prompt(theme: str, *, lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    theme_labels = _get_theme_labels(lang_code)
    theme_label = theme_labels.get(theme, theme_labels.get(DEFAULT_THEME, get_tarot_theme_label(DEFAULT_THEME)))
    examples = _get_theme_examples(lang_code).get(theme, TAROT_THEME_EXAMPLES[DEFAULT_THEME])
    if lang_code == "ja":
        example_text = "』『".join(examples)
    else:
        example_text = "” / “".join(examples)
    return t(lang_code, "TAROT_QUESTION_PROMPT", theme_label=theme_label, example_text=example_text)


def _contains_caution_keyword(text: str) -> bool:
    lowered = text.lower()
    for keyword_list in CAUTION_KEYWORDS.values():
        if any(keyword in lowered for keyword in keyword_list):
            return True
    return False


def append_caution_note(user_text: str, response: str, *, lang: str | None = "ja") -> str:
    if not user_text or not _contains_caution_keyword(user_text):
        return response
    caution_note = get_caution_note(lang)
    separator = "\n\n" if not response.endswith("\n") else "\n"
    return f"{response}{separator}{caution_note}"


def classify_sensitive_topics(text: str) -> set[str]:
    if not text:
        return set()

    lowered = text.lower()
    hits: set[str] = set()
    for topic, keywords in SENSITIVE_TOPICS.items():
        if any(keyword in lowered for keyword in keywords):
            hits.add(topic)
    return hits


def build_sensitive_topic_notice(topics: set[str], *, lang: str | None = "ja") -> str:
    if not topics:
        return ""

    lang_code = normalize_lang(lang)
    topic_labels = [
        t(lang_code, f"SENSITIVE_TOPIC_LABEL_{topic.upper()}") for topic in sorted(topics)
    ]
    joined_labels = " / ".join(topic_labels)
    lines = [
        t(lang_code, "SENSITIVE_TOPIC_NOTICE_HEADER", topics=joined_labels),
        t(lang_code, "SENSITIVE_TOPIC_NOTICE_PRO_HELP"),
    ]
    for topic in sorted(topics):
        guidance_key = f"SENSITIVE_TOPIC_GUIDANCE_{topic.upper()}"
        guidance = t(lang_code, guidance_key)
        if guidance != guidance_key:
            lines.append(f"・{guidance}")

    lines.append(t(lang_code, "SENSITIVE_TOPIC_NOTICE_FOCUS"))
    lines.append(t(lang_code, "SENSITIVE_TOPIC_NOTICE_LIST_REMINDER"))
    return "\n".join(lines)


async def respond_with_safety_notice(message: Message, user_query: str) -> bool:
    topics = classify_sensitive_topics(user_query)
    if not topics:
        return False

    user_id = message.from_user.id if message.from_user else None
    reset_conversation_state(user_id)
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await message.answer(
        build_sensitive_topic_notice(topics, lang=lang), reply_markup=build_quick_menu(user_id)
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
        if not args and "text" not in kwargs:
            kwargs["text"] = None
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


CARD_LINE_PREFIXES = {
    "ja": "《カード》：",
    "en": "《Card》: ",
    "pt": "《Carta》: ",
}
CARD_LINE_PREFIX = CARD_LINE_PREFIXES["ja"]
CARD_LINE_ERROR_TEXT = {
    "ja": "カード情報を取得できませんでした。",
    "en": "Could not retrieve card details.",
    "pt": "Não foi possível obter informações das cartas.",
}
RULES_HEADER = {
    "ja": "出力ルール:",
    "en": "Output rules:",
    "pt": "Regras de saída:",
}


def get_card_line_prefix(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    return CARD_LINE_PREFIXES.get(lang_code, CARD_LINE_PREFIX)


def get_rules_header(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    return RULES_HEADER.get(lang_code, RULES_HEADER["ja"])


def get_caution_note(lang: str | None = "ja") -> str:
    return CAUTION_NOTES.get(normalize_lang(lang), CAUTION_NOTE)


def get_time_range_text(lang: str | None = "ja") -> str:
    return TIME_RANGE_TEXTS.get(normalize_lang(lang), TIME_RANGE_TEXTS["ja"])


def get_rewrite_prompt(lang: str | None = "ja") -> str:
    return REWRITE_PROMPTS.get(normalize_lang(lang), REWRITE_PROMPTS["ja"])

_META_HEADING_PATTERNS = (
    r"^(まとめとして|結論として|総括として|総評として|まとめると|結論から言うと)[、,:：]?\s*",
)


def _strip_meta_prefix(text: str) -> str:
    cleaned = text
    for pattern in _META_HEADING_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned)
    return cleaned.strip()


def _inject_position_headings(
    lines: list[str],
    position_labels: Sequence[str] | None,
    *,
    card_line_prefix: str = CARD_LINE_PREFIX,
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

    card_line_index = None
    for idx, line in enumerate(lines):
        if card_line_prefix in line:
            card_line_index = idx
            break

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
    lang: str | None = "ja",
    card_line_prefix: str | None = None,
) -> str:
    lang_code = normalize_lang(lang)
    effective_prefix = card_line_prefix or get_card_line_prefix(lang_code)
    content = (text or "").strip()
    if not content:
        fallback = {
            "ja": "占い結果をうまく作成できませんでした。もう一度占わせてください。",
            "en": "I couldn't generate the reading properly. May I draw again?",
            "pt": "Não consegui gerar a leitura corretamente. Posso tirar novamente?",
        }
        return fallback.get(lang_code, fallback["ja"])

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
        cleaned = re.sub(r"^引いたカード[：:]", effective_prefix, cleaned)
        cleaned = re.sub(r"^《?(?:カード|Card|Carta)》?[：:]", effective_prefix, cleaned)
        if effective_prefix in cleaned:
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
    compacted = _inject_position_headings(
        compacted,
        position_labels if lang_code == "ja" else None,
        card_line_prefix=effective_prefix,
    )
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
    lang: str | None = "ja",
    card_line_prefix: str | None = None,
) -> str:
    if mode == "tarot":
        return format_tarot_answer(
            text,
            card_line,
            position_labels=position_labels,
            lang=lang,
            card_line_prefix=card_line_prefix,
        )

    content = (text or "").strip()
    if not content:
        fallback = {
            "ja": "少し情報が足りないようです。もう一度教えてくださいね。",
            "en": "I might need a bit more detail. Could you share that again?",
            "pt": "Preciso de um pouco mais de detalhe. Pode me contar de novo?",
        }
        return fallback.get(normalize_lang(lang), fallback["ja"])

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
    reply_markup_first: ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove | None = None,
    reply_markup_last: ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove | None = None,
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


async def _safe_delete_message(message: Message | None) -> None:
    if not message:
        return

    chat_id = getattr(getattr(message, "chat", None), "id", None)
    message_id = getattr(message, "message_id", None)

    if chat_id is None or message_id is None:
        return

    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramBadRequest as exc:
        logger.warning(
            "Failed to delete status message",
            extra={
                "mode": "cleanup",
                "chat_id": chat_id,
                "message_id": message_id,
                "reason": str(exc),
            },
        )
        try:
            await bot.edit_message_text(
                text="\u200b", chat_id=chat_id, message_id=message_id, reply_markup=None
            )
            logger.info(
                "Replaced status message after deletion failure",
                extra={"mode": "cleanup", "chat_id": chat_id, "message_id": message_id},
            )
        except TelegramBadRequest as edit_exc:
            logger.warning(
                "Fallback edit failed while cleaning up status message",
                extra={
                    "mode": "cleanup",
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "reason": str(edit_exc),
                },
            )
        except Exception:
            logger.exception(
                "Unexpected error while editing status message during cleanup",
                extra={"mode": "cleanup", "chat_id": chat_id, "message_id": message_id},
            )
    except Exception:
        logger.exception(
            "Unexpected error while deleting status message",
            extra={"mode": "cleanup", "chat_id": chat_id, "message_id": message_id},
        )


async def _acquire_inflight(
    user_id: int | None,
    message: Message | None = None,
    *,
    busy_message: str | None = None,
    lang: str | None = "ja",
) -> Callable[[], None]:
    def _noop() -> None:
        return None

    if user_id is None:
        return _noop

    lock = USER_REQUEST_LOCKS.setdefault(user_id, asyncio.Lock())
    already_locked = lock.locked()
    if already_locked and message:
        lang_code = normalize_lang(lang)
        reply_text = busy_message if busy_message is not None else t(lang_code, "BUSY_TAROT_MESSAGE")
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


def _should_process_message(
    message: Message,
    *,
    handler: str | None = None,
    allow_language_duplicate: bool = False,
    language_button_hint: str | None = None,
) -> bool:
    # Telegram can resend identical language button taps; keep /lang reachable by letting those duplicates through.
    dedup_key = None
    message_id = getattr(message, "message_id", None)
    chat_id = getattr(getattr(message, "chat", None), "id", None)
    if message_id is not None and chat_id is not None:
        dedup_key = f"{chat_id}:{message_id}"

    if _mark_recent_handled(message):
        if allow_language_duplicate or language_button_hint:
            logger.info(
                "Language dedup check passed",
                extra={
                    "mode": "language",
                    "route": "dedup",
                    "dedup_key": dedup_key,
                    "handler": handler or "unknown",
                    "status": "accepted_new",
                    "language_button_hint": language_button_hint,
                },
            )
        return True

    if allow_language_duplicate:
        logger.info(
            "Bypassing duplicate message for language button",
            extra={
                "mode": "language",
                "route": "dedup",
                "dedup_key": dedup_key,
                "chat_id": chat_id,
                "message_id": message_id,
                "handler": handler or "unknown",
                "language_button_hint": language_button_hint,
                "status": "bypassed_duplicate",
            },
        )
        return True

    logger.info(
        "Skipping duplicate message",
        extra={
            "mode": "router",
            "chat_id": chat_id,
            "message_id": message_id,
            "dedup_key": dedup_key,
            "handler": handler or "unknown",
        },
    )
    return False


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


def _build_charge_retry_keyboard(lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang_code, "GO_TO_STORE_BUTTON"), callback_data="nav:charge")],
            [InlineKeyboardButton(text=t(lang_code, "VIEW_STATUS_BUTTON"), callback_data="nav:status")],
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


def _safe_log_app_event(
    *, event_type: str, user_id: int | None, payload: str | None = None
) -> None:
    request_id = request_id_var.get("-")
    try:
        log_app_event(
            event_type=event_type,
            user_id=user_id,
            request_id=request_id,
            payload=payload,
        )
    except Exception:
        logger.exception(
            "Failed to log app event",
            extra={
                "event_type": event_type,
                "user_id": user_id,
                "payload": payload,
                "request_id": request_id,
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
        lang = get_user_lang_or_default(user_id)
        target = chat_id if chat_id is not None else user_id
        await bot.send_message(
            target, t(lang, "STALE_CALLBACK_MESSAGE"), reply_markup=_build_charge_retry_keyboard(lang)
        )
    except Exception:
        logger.exception("Failed to notify user about stale interaction", extra={"payload": payload, "user_id": user_id})


def build_general_chat_messages(user_query: str, *, lang: str | None = "ja") -> list[dict[str, str]]:
    """通常チャットモードの system prompt を組み立てる。"""
    return [
        {"role": "system", "content": get_consult_system_prompt(lang)},
        {"role": "user", "content": user_query},
    ]


async def call_openai_with_retry(
    messages: Iterable[dict[str, str]], *, lang: str | None = "ja"
) -> tuple[str, bool]:
    prepared_messages = list(messages)
    max_attempts = 3
    base_delay = 1.5
    lang_code = normalize_lang(lang)

    for attempt in range(1, max_attempts + 1):
        try:
            completion = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini", messages=prepared_messages
                ),
            )
            answer = completion.choices[0].message.content
            return postprocess_llm_text(answer, lang=lang_code), False
        except (AuthenticationError, PermissionDeniedError, BadRequestError) as exc:
            logger.exception("Fatal OpenAI error: %s", exc)
            return (
                t(lang_code, "OPENAI_FATAL_ERROR"),
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
                    t(lang_code, "OPENAI_PROCESSING_ERROR"),
                    True,
                )

        delay = base_delay * (2 ** (attempt - 1))
        delay += random.uniform(0, 0.5)
        await asyncio.sleep(delay)

    return t(lang_code, "OPENAI_COMMUNICATION_ERROR"), False


def _preview_text(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def build_lang_keyboard(lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang_code, "LANGUAGE_OPTION_JA"), callback_data="lang:set:ja")],
            [InlineKeyboardButton(text=t(lang_code, "LANGUAGE_OPTION_EN"), callback_data="lang:set:en")],
            [InlineKeyboardButton(text=t(lang_code, "LANGUAGE_OPTION_PT"), callback_data="lang:set:pt")],
        ]
    )


def _strip_invisible(text: str) -> str:
    if not text:
        return ""
    stripped_chars: list[str] = []
    for ch in text:
        if _VARIATION_SELECTOR_RE.match(ch):
            continue
        category = unicodedata.category(ch)
        if category in {"Cf", "Cc"}:
            continue
        stripped_chars.append(ch)
    return "".join(stripped_chars)


def _normalize_language_button_base(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\ufe0e", "").replace("\ufe0f", "")
    # Telegram clients sometimes prepend invisible control characters on button taps; strip them to avoid false negatives.
    return _strip_invisible(normalized)


def _normalize_language_button_text(text: str) -> str:
    if not text:
        return ""
    normalized = _normalize_language_button_base(text)
    normalized = normalized.strip()
    for prefix in GLOBE_EMOJI_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            normalized = normalized.lstrip()
            break
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _has_language_button_prefix(text: str) -> bool:
    if not text:
        return False
    normalized = _normalize_language_button_base(text)
    return normalized.lstrip().startswith(GLOBE_EMOJI_PREFIXES)


def _log_language_button_check(
    *, raw: str, normalized: str, matched: bool, reason: str, hint: str | None
) -> None:
    logger.info(
        "Language button check executed",
        extra={
            "mode": "language",
            "route": "button_check",
            "matched": matched,
            "reason": reason,
            "raw_preview": _preview_text(raw),
            "normalized": normalized or None,
            "hint": hint,
        },
    )


def is_language_reply_button(text: str) -> tuple[bool, str | None]:
    raw = (text or "").strip()
    normalized = _normalize_language_button_text(raw)
    if not normalized:
        if _has_language_button_prefix(raw):
            _log_language_button_check(raw=raw, normalized=normalized, matched=False, reason="empty", hint=None)
        return False, None

    normalized_candidates = {_normalize_language_button_text(label) for label in LANGUAGE_BUTTON_LABELS.values()}
    raw_candidates = {label.strip() for label in LANGUAGE_BUTTON_LABELS.values()}
    if raw in raw_candidates or normalized in normalized_candidates:
        hint = normalized or raw
        _log_language_button_check(raw=raw, normalized=normalized, matched=True, reason="label_match", hint=hint)
        return True, hint

    if not _has_language_button_prefix(raw):
        return False, None

    casefold_candidates = {candidate.casefold() for candidate in normalized_candidates}
    casefold_candidates.update(label.casefold() for label in raw_candidates)
    matched = normalized.casefold() in casefold_candidates
    hint = normalized if matched else None
    _log_language_button_check(
        raw=raw,
        normalized=normalized,
        matched=matched,
        reason="emoji_prefix" if matched else "emoji_prefix_miss",
        hint=hint,
    )
    return matched, hint


def _is_language_button_text(text: str) -> bool:
    matched, _ = is_language_reply_button(text)
    return matched


def _extract_start_payload(message: Message) -> str | None:
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    payload = parts[1].strip()
    if not payload:
        return None
    token = payload.split()[0]
    candidate = token.strip().lower().replace("_", "-")
    if candidate in SUPPORTED_LANGS:
        return candidate
    return None


def resolve_user_lang(message: Message) -> tuple[str, bool]:
    user_id = message.from_user.id if message.from_user else None
    payload_lang = _extract_start_payload(message)
    if payload_lang:
        if user_id is not None:
            set_user_lang(user_id, payload_lang)
        return payload_lang, True

    saved_lang = get_user_lang(user_id) if user_id is not None else None
    if saved_lang:
        return saved_lang, True

    telegram_lang = None
    if message.from_user and getattr(message.from_user, "language_code", None):
        telegram_lang = normalize_lang(message.from_user.language_code)

    return telegram_lang or "ja", False


def get_user_lang_or_default(user_id: int | None) -> str:
    if user_id is None:
        return "ja"
    return get_user_lang(user_id) or "ja"


def build_base_menu(user_id: int | None):
    return base_menu_kb(lang=get_user_lang_or_default(user_id))


def build_quick_menu(
    user_id: int | None,
    *,
    reply_markup: ReplyKeyboardMarkup | InlineKeyboardMarkup | ReplyKeyboardRemove | None = None,
):
    return ensure_quick_menu(reply_markup=reply_markup, lang=get_user_lang_or_default(user_id))


def get_menu_prompt_text(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    prompts = {
        "ja": "下のボタンから次を選べます👇",
        "en": "Choose from the buttons below 👇",
        "pt": "Escolha pelos botões abaixo 👇",
    }
    return prompts.get(lang_code, prompts["ja"])


async def restore_base_menu(message: Message, user_id: int | None, lang: str) -> None:
    lang_code = normalize_lang(lang or "ja")
    prompts = {
        "ja": "ボタンから選択してね👇",
        "en": "Choose from the buttons below 👇",
        "pt": "Escolha pelos botões abaixo 👇",
    }
    restore_text = prompts.get(lang_code, prompts["ja"])
    if not restore_text.strip():
        restore_text = prompts["ja"]
    await message.answer(
        restore_text,
        reply_markup=build_base_menu(user_id),
    )


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
        t(get_user_lang_or_default(user_id), "INACTIVE_RESET_NOTICE"),
        reply_markup=build_base_menu(user_id),
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


def build_tarot_theme_keyboard(*, lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang_code, "TAROT_THEME_BUTTON_LOVE"), callback_data="tarot_theme:love")],
            [InlineKeyboardButton(text=t(lang_code, "TAROT_THEME_BUTTON_MARRIAGE"), callback_data="tarot_theme:marriage")],
            [InlineKeyboardButton(text=t(lang_code, "TAROT_THEME_BUTTON_WORK"), callback_data="tarot_theme:work")],
            [InlineKeyboardButton(text=t(lang_code, "TAROT_THEME_BUTTON_LIFE"), callback_data="tarot_theme:life")],
        ]
    )


# --- Share funnel (Step3) ---
BOT_PUBLIC_LINK = "https://t.me/tarot78_catbot"
BOT_START_LINK = "https://t.me/tarot78_catbot?start=from_share"

SHARE_TEXT_BY_LANG: dict[str, str] = {
    "en": "Daily Tarot in 1 tap 🐈✨ Try @tarot78_catbot",
    "ja": "1タップで今日のタロット🐈✨ 試してみて → @tarot78_catbot",
    "pt": "Tarô diário em 1 toque 🐈✨ Experimente @tarot78_catbot",
}


def build_share_url(*, lang: str | None = "en") -> str:
    try:
        lang_code = normalize_lang(lang or "en")
    except Exception:
        lang_code = (lang or "en").lower()
    text = SHARE_TEXT_BY_LANG.get(lang_code, SHARE_TEXT_BY_LANG["en"])
    query = urlencode({"url": BOT_PUBLIC_LINK, "text": text})
    return f"https://t.me/share/url?{query}"


def build_share_start_keyboard(*, lang: str | None = "en") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Share", url=build_share_url(lang=lang)),
                InlineKeyboardButton(text="Start", url=BOT_START_LINK),
            ]
        ]
    )


def merge_inline_keyboards(*markups: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup | None:
    rows: list[list[InlineKeyboardButton]] = []
    for markup in markups:
        if not markup:
            continue
        kb = getattr(markup, "inline_keyboard", None)
        if kb:
            rows.extend(kb)
    return InlineKeyboardMarkup(inline_keyboard=rows) if rows else None


def build_upgrade_keyboard(*, lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang_code, "UPGRADE_BUTTON_TEXT"), callback_data="upgrade_to_three")]
        ]
    )


async def prompt_tarot_mode(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "tarot")
    set_tarot_theme(user_id, DEFAULT_THEME)
    set_tarot_flow(user_id, "awaiting_theme")
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await message.answer(t(lang, "TAROT_THEME_PROMPT"), reply_markup=build_base_menu(user_id))
    await message.answer(
        t(lang, "TAROT_THEME_SELECT_PROMPT"),
        reply_markup=build_tarot_theme_keyboard(lang=lang),
    )


async def prompt_consult_mode(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "consult")
    reset_tarot_state(user_id)
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await message.answer(t(lang, "CONSULT_MODE_PROMPT"), reply_markup=build_base_menu(user_id))


async def prompt_charge_menu(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "charge")
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await message.answer(t(lang, "CHARGE_MODE_PROMPT"), reply_markup=build_base_menu(user_id))
    await send_store_menu(message)


async def prompt_status(message: Message, *, now: datetime) -> None:
    user_id = message.from_user.id if message.from_user else None
    set_user_mode(user_id, "status")
    mark_user_active(user_id, now=now)
    lang = get_user_lang_or_default(user_id)
    if user_id is None:
        await message.answer(
            t(lang, "USER_INFO_DM_REQUIRED"),
            reply_markup=build_base_menu(user_id),
        )
        return
    user = get_user_with_default(user_id) or ensure_user(user_id, now=now)
    await message.answer(
        format_status(user, now=now, lang=lang), reply_markup=build_base_menu(user_id)
    )


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
        theme=effective_theme,
    )


def get_start_text(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    return t(lang_code, "START_TEXT")


def get_store_intro_text(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    return t(lang_code, "STORE_INTRO_TEXT")


def consume_ticket_for_spread(user_id: int, spread: Spread) -> bool:
    column = SPREAD_TICKET_COLUMNS.get(spread.id)
    if not column:
        return False
    return consume_ticket(user_id, ticket=column)


def format_status(user: UserRecord, *, now: datetime | None = None, lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    now = now or utcnow()
    pass_until = effective_pass_expires_at(user.user_id, user, now)
    has_pass = effective_has_pass(user.user_id, user, now=now)
    admin_mode = is_admin_user(user.user_id)
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

    status_title = t(lang_code, "STATUS_TITLE_ADMIN" if admin_mode else "STATUS_TITLE")
    general_line_localized: str
    if has_pass:
        general_line_localized = t(lang_code, "STATUS_GENERAL_PASS")
    elif trial_days_left > 0:
        general_line_localized = t(
            lang_code,
            "STATUS_GENERAL_TRIAL",
            trial_days_left=trial_days_left,
            remaining=general_remaining,
        )
    else:
        general_line_localized = t(lang_code, "STATUS_GENERAL_LOCKED")

    pass_label_localized: str
    if pass_until:
        remaining_days = (_usage_today(pass_until) - _usage_today(now)).days
        remaining_hint = (
            t(lang_code, "STATUS_PASS_REMAINING", remaining_days=remaining_days)
            if remaining_days >= 0
            else ""
        )
        pass_label_localized = (
            f"{pass_until.astimezone(USAGE_TIMEZONE).strftime('%Y-%m-%d %H:%M JST')} {remaining_hint}".strip()
        )
        if admin_mode:
            pass_label_localized = f"{pass_label_localized} ({t(lang_code, 'STATUS_ADMIN_LABEL')})"
    else:
        pass_label_localized = t(lang_code, "STATUS_PASS_NONE")

    latest_payment = get_latest_payment(user.user_id)
    recent_purchase_line = ""
    if latest_payment:
        product = get_product(latest_payment.sku)
        label = _get_product_title(product, lang_code) if product else latest_payment.sku
        purchased_at = latest_payment.created_at.astimezone(USAGE_TIMEZONE).strftime("%Y-%m-%d %H:%M JST")
        recent_purchase_line = t(
            lang_code,
            "STATUS_LATEST_PURCHASE",
            label=label,
            sku=latest_payment.sku,
            purchased_at=purchased_at,
        )

    lines = [
        status_title,
        t(lang_code, "STATUS_TRIAL_LINE", trial_day=trial_day),
        t(lang_code, "STATUS_PASS_LABEL", pass_label=pass_label_localized),
        t(
            lang_code,
            "STATUS_ONE_ORACLE",
            limit=one_oracle_limit,
            remaining=one_remaining,
        ),
        t(lang_code, "STATUS_GENERAL", text=general_line_localized),
        t(lang_code, "STATUS_TICKET_3", count=user.tickets_3),
        t(lang_code, "STATUS_TICKET_7", count=user.tickets_7),
        t(lang_code, "STATUS_TICKET_10", count=user.tickets_10),
        t(
            lang_code,
            "STATUS_IMAGES",
            state=t(lang_code, "STATUS_IMAGES_ON" if user.images_enabled else "STATUS_IMAGES_OFF"),
        ),
        t(lang_code, "STATUS_RESET", reset_time=format_next_reset(now)),
    ]
    if recent_purchase_line:
        lines.append(recent_purchase_line)
    if admin_mode:
        lines.insert(1, t(lang_code, "STATUS_ADMIN_FLAG"))
    return "\n".join(lines)


def build_unlock_text(product: Product, user: UserRecord, *, lang: str | None = "ja") -> str:
    now = utcnow()
    lang_code = normalize_lang(lang)
    title = _get_product_title(product, lang_code)
    if product.sku in TICKET_SKU_TO_COLUMN:
        column = TICKET_SKU_TO_COLUMN[product.sku]
        balance = getattr(user, column)
        return t(lang_code, "UNLOCK_TICKET_ADDED", product=title, balance=balance)

    if product.sku.startswith("PASS_"):
        until = user.premium_until or user.pass_until
        duration = title
        if until:
            until_local = until.astimezone(USAGE_TIMEZONE)
            remaining_days = (_usage_today(until) - _usage_today(now)).days
            remaining_hint = (
                t(lang_code, "STATUS_PASS_REMAINING", remaining_days=remaining_days)
                if remaining_days >= 0
                else ""
            )
            until_text = until_local.strftime("%Y-%m-%d %H:%M JST")
        else:
            until_text = t(lang_code, "PASS_EXTENDED_TEXT")
            remaining_hint = ""
        return t(
            lang_code,
            "UNLOCK_PASS_GRANTED",
            duration=duration,
            until_text=until_text,
            remaining_hint=remaining_hint,
        )

    if product.sku == "ADDON_IMAGES":
        return t(lang_code, "UNLOCK_IMAGES_ENABLED")

    return t(lang_code, "PURCHASE_GENERIC_THANKS")


def build_tarot_messages(
    *,
    spread: Spread,
    user_query: str,
    drawn_cards: list[dict[str, str]],
    short: bool = False,
    theme: str | None = None,
    action_count: int | None = None,
    lang: str | None = "ja",
) -> list[dict[str, str]]:
    lang_code = normalize_lang(lang)
    is_time_axis = spread.id == THREE_CARD_TIME_AXIS.id
    rules = get_tarot_output_rules(time_axis=is_time_axis, short=short, lang=lang_code)
    rules_text = "\n".join(f"- {rule}" for rule in rules)
    tarot_system_prompt = (
        f"{get_tarot_system_prompt(theme, time_axis=is_time_axis, lang=lang_code)}\n"
        f"{get_rules_header(lang_code)}\n{rules_text}"
    )
    theme_focus = theme_instructions(theme, lang=lang_code)
    format_template = get_tarot_fixed_output_format(lang_code, time_axis=is_time_axis)
    if is_time_axis:
        if lang_code == "ja":
            action_count_text = "- 箇条書きは未来パートにのみ最大3点まで。過去と現在では使わない。"
            scope_text = "- 時間の目安が無い場合は前後3か月の流れとして触れる。"
            format_hint = (
                "過去・現在・未来の時間軸リーディングです。見出しや章ラベルを使わず、次の並びと改行を必ず守ってください:\n"
                f"{format_template}\n"
                f"{action_count_text}\n"
                f"{scope_text}\n"
                "- カード名は各ブロックの《カード》行で必ず書く。🃏などの絵文字は禁止。\n"
                f"- テーマ別フォーカス: {theme_focus}"
            )
        elif lang_code == "pt":
            action_count_text = "- Use tópicos apenas no bloco do futuro, no máximo 3. Não use no passado/presente."
            scope_text = "- Se não houver prazo, considere cerca de 3 meses de fluxo."
            format_hint = (
                "Leitura em linha do tempo (passado/presente/futuro). Não use títulos; siga a ordem e quebras abaixo:\n"
                f"{format_template}\n"
                f"{action_count_text}\n"
                f"{scope_text}\n"
                "- Cada bloco precisa da linha “《Carta》” com nome e orientação; evite emojis como 🃏.\n"
                f"- Foco do tema: {theme_focus}"
            )
        else:
            action_count_text = "- Bullets only in the future block, maximum 3. Do not use them for past/present."
            scope_text = "- If no time scale is given, read it as about 3 months of flow."
            format_hint = (
                "This is a past–present–future reading. No headings; keep this order and line breaks:\n"
                f"{format_template}\n"
                f"{action_count_text}\n"
                f"{scope_text}\n"
                "- Each block must include the card name on the “《Card》” line; avoid emojis like 🃏.\n"
                f"- Theme focus: {theme_focus}"
            )
    else:
        if action_count is not None:
            if action_count == 4:
                if lang_code == "ja":
                    action_count_text = "- 次の一手は必ず4個。内容が薄い場合は各項目を短くしないで具体化する。"
                elif lang_code == "pt":
                    action_count_text = "- Traga exatamente 4 próximos passos. Se estiverem rasos, deixe cada item mais concreto."
                else:
                    action_count_text = "- Provide exactly 4 next steps. If they feel thin, make each item concrete."
            elif action_count in {2, 3}:
                if lang_code == "ja":
                    action_count_text = (
                        f"- 次の一手は必ず{action_count}個。4個は禁止。必要な要素は各項目に統合して良い。"
                    )
                elif lang_code == "pt":
                    action_count_text = (
                        f"- Entregue exatamente {action_count} próximos passos. Não adicione um 4º; combine ideias se precisar."
                    )
                else:
                    action_count_text = (
                        f"- Provide exactly {action_count} next steps. Do not add a 4th; merge ideas when needed."
                    )
            else:
                if lang_code == "ja":
                    action_count_text = "- 次の一手はシステムの指示個数を守り、必要でも4個までに抑える。"
                elif lang_code == "pt":
                    action_count_text = "- Use o número pedido de próximos passos; no máximo 4 mesmo se precisar mais."
                else:
                    action_count_text = "- Follow the requested number of next steps; cap them at 4 even if you need more."
        else:
            if lang_code == "ja":
                action_count_text = "- 次の一手は2〜3個を基本に、必要なときだけ4個まで。"
            elif lang_code == "pt":
                action_count_text = "- Use 2–3 próximos passos como padrão e só chegue a 4 se for necessário."
            else:
                action_count_text = "- Default to 2–3 next steps; use up to 4 only when needed."
        format_hint = (
            (
                "必ず次の順序と改行で、見出しや絵文字を使わずに書いてください:\n"
                f"{format_template}\n"
                f"{action_count_text}\n"
                "- 1枚引きは350〜650字、3枚以上は550〜900字を目安に、1400文字以内に収める。\n"
                "- カード名は「《カード》：」行で1回だけ伝える。🃏などの絵文字は禁止。\n"
                f"- テーマ別フォーカス: {theme_focus}"
            )
            if lang_code == "ja"
            else (
                "Follow this order and line breaks without headings or emojis:\n"
                f"{format_template}\n"
                f"{action_count_text}\n"
                "- Aim for 350–650 characters for 1 card; 550–900 for 3+; keep under 1400.\n"
                '- Give the card name only once on the "《Card》" line; no 🃏 emojis.\n'
                f"- Theme focus: {theme_focus}"
            )
            if lang_code == "en"
            else (
                "Siga esta ordem e quebras de linha, sem títulos nem emojis:\n"
                f"{format_template}\n"
                f"{action_count_text}\n"
                "- Mire em 350–650 caracteres para 1 carta; 550–900 para 3+; mantenha abaixo de 1400.\n"
                '- Informe o nome da carta só uma vez na linha "《Carta》"; sem emoji 🃏.\n'
                f"- Foco do tema: {theme_focus}"
            )
        )

    tarot_payload = {
        "spread_id": spread.id,
        "spread_name_ja": spread.name_ja,
        "positions": drawn_cards,
        "user_question": user_query,
        "user_lang": lang_code,
    }

    return [
        {"role": "system", "content": tarot_system_prompt},
        {"role": "system", "content": format_hint},
        {"role": "assistant", "content": json.dumps(tarot_payload, ensure_ascii=False, indent=2)},
        {"role": "user", "content": user_query},
    ]


def format_drawn_cards(drawn_cards: list[dict[str, str]], *, lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    prefix = get_card_line_prefix(lang_code)
    if not drawn_cards:
        message = CARD_LINE_ERROR_TEXT.get(lang_code, CARD_LINE_ERROR_TEXT["ja"])
        return f"{prefix}{message}"

    card_labels = []
    for item in drawn_cards:
        card = item.get("card", {})
        card_name = (
            card.get(f"name_{lang_code}")
            or card.get("name_en")
            or card.get("name_ja")
            or "不明なカード"
        )
        orientation_label = card.get(f"orientation_label_{lang_code}")
        if not orientation_label:
            orientation = (card.get("orientation") or "").lower()
            orientation_label = orientation_label_by_lang(orientation == "reversed", lang_code)
        if lang_code == "ja":
            card_label = f"{card_name}（{orientation_label}）" if orientation_label else card_name
        else:
            card_label = f"{card_name} ({orientation_label})" if orientation_label else card_name
        position_label = item.get(f"label_{lang_code}") if lang_code != "ja" else item.get("label_ja")
        if position_label and position_label.strip() != "メインメッセージ":
            card_labels.append(f"{card_label} - {position_label}")
        else:
            card_labels.append(card_label)
    separator = "、" if lang_code == "ja" else ", "
    return prefix + separator.join(card_labels)


def ensure_tarot_response_prefixed(
    answer: str, heading: str, *, card_line_prefix: str | None = None
) -> str:
    prefix = card_line_prefix or CARD_LINE_PREFIX
    if answer.lstrip().startswith(prefix):
        return answer
    return f"{heading}\n{answer}" if heading else answer


async def rewrite_chat_response(original: str, *, lang: str | None = "ja") -> tuple[str, bool]:
    rewrite_prompt = get_rewrite_prompt(lang)

    messages = [
        {"role": "system", "content": rewrite_prompt},
        {"role": "user", "content": original},
    ]

    return await call_openai_with_retry(messages, lang=lang)


async def ensure_general_chat_safety(
    answer: str, *, rewrite_func=rewrite_chat_response, lang: str | None = "ja"
) -> str:
    if not contains_tarot_like(answer):
        return answer

    try:
        rewritten, fatal = await rewrite_func(answer, lang=lang)
    except TypeError as exc:
        try:
            rewritten, fatal = await rewrite_func(answer)
        except Exception:
            logger.exception("Unexpected error during chat rewrite", exc_info=True)
            rewritten, fatal = "", False
        else:
            logger.warning("Rewrite function does not accept lang parameter: %s", exc)
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


def get_terms_text(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    support_email = get_support_email()
    return t(lang_code, "TERMS_TEXT", support_email=support_email)


def get_support_text(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    support_email = get_support_email()
    return t(lang_code, "SUPPORT_TEXT", support_email=support_email)


def get_pay_support_text(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    support_email = get_support_email()
    return t(lang_code, "PAY_SUPPORT_TEXT", support_email=support_email)

def get_terms_prompt_before_buy(lang: str | None = "ja") -> str:
    lang_code = normalize_lang(lang)
    return t(lang_code, "TERMS_PROMPT_BEFORE_BUY")


def build_terms_keyboard(include_buy_option: bool = False, *, lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    rows = [[InlineKeyboardButton(text=t(lang_code, "TERMS_BUTTON_AGREE"), callback_data=TERMS_CALLBACK_AGREE)]]
    if include_buy_option:
        rows.append(
            [InlineKeyboardButton(text=t(lang_code, "TERMS_BUTTON_AGREE_AND_BUY"), callback_data=TERMS_CALLBACK_AGREE_AND_BUY)]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_terms_prompt_keyboard(lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang_code, "TERMS_BUTTON_VIEW"), callback_data=TERMS_CALLBACK_SHOW)],
            [InlineKeyboardButton(text=t(lang_code, "TERMS_BUTTON_AGREE"), callback_data=TERMS_CALLBACK_AGREE)],
            [
                InlineKeyboardButton(
                    text=t(lang_code, "TERMS_BUTTON_AGREE_AND_BUY"), callback_data=TERMS_CALLBACK_AGREE_AND_BUY
                )
            ],
        ]
    )


def _get_product_title(product: Product, lang: str) -> str:
    return t(lang, f"PRODUCT_{product.sku}_TITLE")


def _get_product_description(product: Product, lang: str) -> str:
    return t(lang, f"PRODUCT_{product.sku}_DESCRIPTION")


def build_store_keyboard(lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    rows: list[list[InlineKeyboardButton]] = []
    for product in iter_products():
        if product.sku == "ADDON_IMAGES" and not IMAGE_ADDON_ENABLED:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=t(lang_code, "ADDON_PENDING_LABEL"),
                        callback_data="addon:pending",
                    )
                ]
            )
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{_get_product_title(product, lang_code)} - {product.price_stars}⭐️",
                    callback_data=f"buy:{product.sku}"
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_purchase_followup_keyboard(lang: str | None = "ja") -> InlineKeyboardMarkup:
    lang_code = normalize_lang(lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang_code, "RETURN_TO_TAROT_BUTTON"), callback_data="nav:menu")],
            [InlineKeyboardButton(text=t(lang_code, "VIEW_STATUS_BUTTON"), callback_data="nav:status")],
        ]
    )


async def send_store_menu(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    lang = get_user_lang_or_default(user_id)
    await message.answer(
        get_store_intro_text(lang=lang), reply_markup=build_store_keyboard(lang=lang)
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not _should_process_message(message, handler="help"):
        return

    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await message.answer(build_help_text(lang=lang), reply_markup=build_quick_menu(user_id))


@dp.message(Command("terms"))
async def cmd_terms(message: Message) -> None:
    if not _should_process_message(message, handler="terms"):
        return

    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    if user_id is not None:
        ensure_user(user_id)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip().lower() == "agree" and user_id is not None:
        set_terms_accepted(user_id)
        await message.answer(
            t(lang, "TERMS_AGREED_RECORDED"),
            reply_markup=build_quick_menu(user_id),
        )
        return

    await message.answer(get_terms_text(lang=lang), reply_markup=build_terms_keyboard(lang=lang))
    await message.answer(t(lang, "TERMS_NEXT_STEP_REMINDER"), reply_markup=build_quick_menu(user_id))


@dp.callback_query(F.data == TERMS_CALLBACK_SHOW)
async def handle_terms_show(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    lang = get_user_lang_or_default(query.from_user.id if query.from_user else None)
    if query.message:
        await query.message.answer(
            get_terms_text(lang=lang),
            reply_markup=build_terms_prompt_keyboard(lang=lang)
        )


@dp.callback_query(F.data == TERMS_CALLBACK_AGREE)
async def handle_terms_agree(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    lang = get_user_lang_or_default(user_id)
    if user_id is None:
        await _safe_answer_callback(query, t(lang, "USER_INFO_MISSING"), show_alert=True)
        return

    set_terms_accepted(user_id)
    await _safe_answer_callback(query, t(lang, "TERMS_AGREED_RECORDED"), show_alert=True)
    if query.message:
        await query.message.answer(
            t(lang, "TERMS_AGREED_RECORDED"),
            reply_markup=build_quick_menu(user_id),
        )


@dp.callback_query(F.data == TERMS_CALLBACK_AGREE_AND_BUY)
async def handle_terms_agree_and_buy(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    lang = get_user_lang_or_default(user_id)
    if user_id is None:
        await _safe_answer_callback(query, t(lang, "USER_INFO_MISSING"), show_alert=True)
        return

    set_terms_accepted(user_id)
    await _safe_answer_callback(query, t(lang, "TERMS_AGREED_RECORDED"), show_alert=True)
    if query.message:
        await send_store_menu(query.message)
    else:
        await bot.send_message(
            user_id,
            get_store_intro_text(lang=lang),
            reply_markup=build_store_keyboard(lang=lang),
        )


@dp.message(Command("support"))
async def cmd_support(message: Message) -> None:
    if not _should_process_message(message, handler="support"):
        return

    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await message.answer(
        get_support_text(lang=lang), reply_markup=build_quick_menu(user_id)
    )


@dp.message(Command("paysupport"))
async def cmd_pay_support(message: Message) -> None:
    if not _should_process_message(message, handler="paysupport"):
        return

    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    lang = get_user_lang_or_default(message.from_user.id if message.from_user else None)
    await message.answer(get_pay_support_text(lang=lang))


@dp.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    if not _should_process_message(message, handler="buy"):
        return

    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    if user_id is not None:
        ensure_user(user_id)
        if not has_accepted_terms(user_id):
            followup = t(lang, "TERMS_PROMPT_REMINDER")
            await message.answer(
                followup,
                reply_markup=build_terms_prompt_keyboard(lang=lang),
            )
            return

    await prompt_charge_menu(message)


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not _should_process_message(message, handler="status"):
        return

    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    now = utcnow()
    await prompt_status(message, now=now)


@dp.message(Command("feedback"))
async def cmd_feedback(message: Message) -> None:
    if not _should_process_message(message, handler="feedback"):
        return

    user_id = message.from_user.id if message.from_user else None
    lang = get_user_lang_or_default(user_id)
    if user_id is None:
        await message.answer(t(lang, "FEEDBACK_DM_REQUIRED"))
        return
    reset_state_for_explicit_command(user_id)
    mark_user_active(user_id)
    menu = build_base_menu(user_id)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            t(lang, "FEEDBACK_PROMPT"),
            reply_markup=menu,
        )
        return

    feedback_text = parts[1].strip()
    mode = get_user_mode(user_id)
    try:
        log_feedback(
            user_id=user_id,
            mode=mode,
            text=feedback_text,
            request_id=request_id_var.get("-"),
        )
        _safe_log_app_event(
            event_type="feedback",
            user_id=user_id,
            payload=json.dumps({"mode": mode}),
        )
    except Exception:
        logger.exception("Failed to record feedback", extra={"user_id": user_id})
        await message.answer(
            t(lang, "FEEDBACK_SAVE_ERROR"),
            reply_markup=menu,
        )
        return

    await message.answer(
        t(lang, "FEEDBACK_THANKS"), reply_markup=menu
    )


@dp.message(Command("read1"))
async def cmd_read1(message: Message) -> None:
    if not _should_process_message(message, handler="read1"):
        return

    reset_state_for_explicit_command(message.from_user.id if message.from_user else None)
    mark_user_active(message.from_user.id if message.from_user else None)
    await prompt_tarot_mode(message)


@dp.message(Command("love1"))
async def cmd_love1(message: Message) -> None:
    if not _should_process_message(message, handler="love1"):
        return

    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    set_user_mode(user_id, "tarot")
    set_tarot_theme(user_id, "love")
    set_tarot_flow(user_id, "awaiting_question")
    mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await message.answer(
        build_tarot_question_prompt("love", lang=lang), reply_markup=build_base_menu(user_id)
    )


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not _should_process_message(message, handler="start"):
        return

    user_id = message.from_user.id if message.from_user else None
    reset_state_for_explicit_command(user_id)
    set_user_mode(user_id, "consult")
    reset_tarot_state(user_id)
    mark_user_active(user_id)
    lang, is_persisted = resolve_user_lang(message)
    if not is_persisted:
        prompt = f"{t(lang, 'LANGUAGE_SELECT_PROMPT')}\n\n{get_start_text(lang=lang)}"
        await message.answer(
            prompt,
            reply_markup=build_lang_keyboard(lang=lang),
        )
        return

    await message.answer(get_start_text(lang=lang), reply_markup=base_menu_kb(lang=lang))


@dp.message(Command("lang"))
async def cmd_lang(message: Message, *, skip_dedup: bool = False) -> None:
    if not skip_dedup and not _should_process_message(message, handler="lang"):
        return
    logger.info(
        "Entered /lang handler",
        extra={
            "mode": "language",
            "route": "command",
            "user_id": getattr(getattr(message, "from_user", None), "id", None),
            "skip_dedup": skip_dedup,
            "message_id": getattr(message, "message_id", None),
        },
    )

    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        await message.answer(t("ja", "USER_INFO_MISSING"))
        return
    lang = get_user_lang_or_default(user_id)
    await message.answer(
        t(lang, "LANGUAGE_SELECT_PROMPT"),
        reply_markup=build_lang_keyboard(lang=lang),
    )


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
            t(get_user_lang_or_default(user_id), "MENU_RETURNED_TEXT"),
            reply_markup=build_base_menu(user_id),
        )


@dp.callback_query(F.data.startswith("lang:set:"))
async def handle_lang_set(query: CallbackQuery) -> None:
    await _safe_answer_callback(query, cache_time=1)
    data = query.data or ""
    lang_code = data.split(":", maxsplit=2)[-1] if ":" in data else None
    normalized = normalize_lang(lang_code) if lang_code else None
    user_id = query.from_user.id if query.from_user else None

    if normalized not in SUPPORTED_LANGS or user_id is None:
        if query.message:
            await query.message.answer(t("ja", "LANGUAGE_SET_FAILED"))
        return

    set_user_lang(user_id, normalized)
    set_user_mode(user_id, "consult")
    reset_tarot_state(user_id)
    mark_user_active(user_id)
    lang_label_map = {
        "ja": t("ja", "LANGUAGE_OPTION_JA"),
        "en": t("en", "LANGUAGE_OPTION_EN"),
        "pt": t("pt", "LANGUAGE_OPTION_PT"),
    }
    lang_label = lang_label_map.get(normalized, normalized)
    confirmation = t(normalized, "LANGUAGE_SET_CONFIRMATION", language=lang_label)
    reply_markup = base_menu_kb(lang=normalized)
    start_text = get_start_text(lang=normalized)
    if query.message:
        await query.message.answer(confirmation, reply_markup=reply_markup)
        await query.message.answer(start_text, reply_markup=reply_markup)
    else:
        await bot.send_message(user_id, confirmation, reply_markup=reply_markup)
        await bot.send_message(user_id, start_text, reply_markup=reply_markup)


@dp.callback_query(F.data == "nav:status")
async def handle_nav_status(query: CallbackQuery, state: FSMContext) -> None:
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await _safe_answer_callback(query, t("ja", "USER_INFO_MISSING"), show_alert=True)
        return
    await state.clear()
    set_user_mode(user_id, "status")
    mark_user_active(user_id)
    now = utcnow()
    lang = get_user_lang_or_default(user_id)
    user = get_user_with_default(user_id) or ensure_user(user_id, now=now)
    formatted = format_status(user, now=now, lang=lang)
    if query.message:
        await query.message.answer(formatted, reply_markup=build_base_menu(user_id))
    else:
        await bot.send_message(user_id, formatted, reply_markup=build_base_menu(user_id))


@dp.callback_query(F.data == "nav:charge")
async def handle_nav_charge(query: CallbackQuery, state: FSMContext) -> None:
    await _safe_answer_callback(query, cache_time=1)
    user_id = query.from_user.id if query.from_user else None
    if user_id is not None:
        ensure_user(user_id)
        set_user_mode(user_id, "charge")
        mark_user_active(user_id)
    lang = get_user_lang_or_default(user_id)
    await state.clear()
    if query.message:
        await prompt_charge_menu(query.message)
    elif user_id is not None:
        await bot.send_message(
            user_id, t(lang, "CHARGE_MODE_PROMPT"), reply_markup=build_base_menu(user_id)
        )
        await bot.send_message(
            user_id,
            get_store_intro_text(lang=lang),
            reply_markup=build_store_keyboard(lang=lang),
        )


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
    lang = get_user_lang_or_default(user_id)
    _safe_log_payment_event(
        user_id=user_id, event_type="buy_click", sku=product.sku, payload=query.data
    )
    if product.sku == "ADDON_IMAGES" and not IMAGE_ADDON_ENABLED:
        await _safe_answer_callback(
            query, t(lang, "ADDON_PENDING_ALERT"), show_alert=True
        )
        return
    if not has_accepted_terms(user_id):
        terms_prompt = get_terms_prompt_before_buy(lang)
        await _safe_answer_callback(query, terms_prompt, show_alert=True)
        if query.message:
            followup = t(lang, "TERMS_PROMPT_REMINDER")
            await query.message.answer(
                followup,
                reply_markup=build_terms_prompt_keyboard(lang=lang),
            )
        return

    if product.sku == "TICKET_3":
        has_pass = effective_has_pass(user_id, user, now=now)
        if has_pass:
            await _safe_answer_callback(
                query,
                t(lang, "PASS_ALREADY_ACTIVE_ALERT"),
                show_alert=True,
            )
            if query.message:
                await query.message.answer(
                    t(lang, "PASS_ALREADY_ACTIVE_MESSAGE"),
                    reply_markup=build_base_menu(user_id),
                )
            return

    if _check_purchase_dedup(user_id, product.sku):
        _safe_log_payment_event(
            user_id=user_id, event_type="buy_dedup_hit", sku=product.sku, payload=query.data
        )
        await _safe_answer_callback(
            query,
            t(lang, "PURCHASE_DEDUP_ALERT"),
            show_alert=True,
        )
        if query.message:
            await query.message.answer(
                t(lang, "PURCHASE_DEDUP_MESSAGE"),
                reply_markup=build_base_menu(user_id),
            )
        return
    payload = json.dumps({"sku": product.sku, "user_id": user_id})
    title_localized = _get_product_title(product, lang)
    description_localized = _get_product_description(product, lang)
    prices = [LabeledPrice(label=title_localized, amount=product.price_stars)]

    if query.message:
        try:
            await query.message.answer_invoice(
                title=title_localized,
                description=description_localized,
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
                t(lang, "INVOICE_DISPLAY_FAILED"),
                reply_markup=_build_charge_retry_keyboard(lang),
            )
            return
    await _safe_answer_callback(query, t(lang, "OPENING_PAYMENT_SCREEN"))


@dp.callback_query(F.data == "addon:pending")
async def handle_addon_pending(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    lang = get_user_lang_or_default(query.from_user.id if query.from_user else None)
    await _safe_answer_callback(query, t(lang, "ADDON_PENDING_ALERT"), show_alert=True)


@dp.callback_query(F.data.startswith("tarot_theme:"))
async def handle_tarot_theme_select(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    data = query.data or ""
    _, _, theme = data.partition(":")
    user_id = query.from_user.id if query.from_user else None
    mark_user_active(user_id)
    if theme not in {"love", "marriage", "work", "life"}:
        lang = get_user_lang_or_default(user_id)
        await _safe_answer_callback(query, t(lang, "UNKNOWN_THEME"), show_alert=True)
        return

    set_user_mode(user_id, "tarot")
    set_tarot_theme(user_id, theme)
    set_tarot_flow(user_id, "awaiting_question")
    lang = get_user_lang_or_default(user_id)
    await _safe_answer_callback(query, t(lang, "TAROT_THEME_SET_CONFIRMATION"))
    if query.message:
        prompt_text = build_tarot_question_prompt(theme, lang=lang)
        await query.message.edit_text(prompt_text)
    elif user_id is not None:
        await bot.send_message(user_id, build_tarot_question_prompt(theme, lang=lang))


@dp.callback_query(F.data == "upgrade_to_three")
async def handle_upgrade_to_three(query: CallbackQuery):
    await _safe_answer_callback(query, cache_time=1)
    if query.message:
        lang = get_user_lang_or_default(query.from_user.id if query.from_user else None)
        await query.message.answer(
            "3枚スプレッドで深掘りするには /buy からチケットを購入してください。\n"
            "決済が未開放の場合は少しお待ちください。",
            reply_markup=build_store_keyboard(lang=lang),
        )


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    sku, payload_user_id = _parse_invoice_payload(pre_checkout_query.invoice_payload or "")
    product = get_product(sku) if sku else None
    user_id = pre_checkout_query.from_user.id if pre_checkout_query.from_user else None
    log_user_id = user_id or payload_user_id
    lang = get_user_lang_or_default(log_user_id)
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
            error_message=t(lang, "PRODUCT_INFO_MISSING"),
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
            error_message=t(lang, "PURCHASER_INFO_MISSING"),
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
    lang = get_user_lang_or_default(user_id)
    lang_code = normalize_lang(lang)
    if user_id_message is not None and user_id is not None and user_id != user_id_message:
        await message.answer(
            t(lang_code, "PAYMENT_INFO_MISMATCH")
        )
        return

    if not product or user_id is None:
        await message.answer(
            t(lang_code, "PAYMENT_VERIFICATION_DELAY")
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
            t(lang_code, "PAYMENT_ALREADY_PROCESSED"),
            reply_markup=build_purchase_followup_keyboard(lang=lang_code),
        )
        return
    updated_user = grant_purchase(user_id, product.sku)
    unlock_message = build_unlock_text(product, updated_user, lang=lang_code)
    title_localized = _get_product_title(product, lang_code)
    thank_you_lines = [
        t(lang_code, "PURCHASE_THANK_YOU", product=title_localized),
        unlock_message,
        t(lang_code, "PURCHASE_STATUS_REMINDER"),
        t(lang_code, "PURCHASE_NAVIGATION_HINT"),
    ]
    await message.answer(
        "\n".join(thank_you_lines), reply_markup=build_purchase_followup_keyboard(lang=lang_code)
    )


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
    if not _should_process_message(message, handler="admin"):
        return

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
            "・/admin feedback_recent [N] : 直近のフィードバックを確認します。\n"
            "・/admin stats [days] : 日次の占い/相談/決済/エラー件数を確認します。\n"
            f"SKU候補: {valid_skus}"
        )
        return

    subcommand = parts[1].lower()
    if subcommand == "feedback_recent":
        limit = 10
        if len(parts) >= 3:
            try:
                limit = max(1, min(50, int(parts[2])))
            except ValueError:
                await message.answer("件数は数字で指定してください。例: /admin feedback_recent 20")
                return
        records = get_recent_feedback(limit)
        if not records:
            await message.answer("まだフィードバックが登録されていません。")
            return
        lines = []
        for record in records:
            created_local = record.created_at.astimezone(USAGE_TIMEZONE).strftime("%Y-%m-%d %H:%M")
            preview = record.text if len(record.text) <= 120 else record.text[:117] + "..."
            lines.append(
                f"{created_local} | uid={record.user_id} | mode={record.mode} | rid={record.request_id or '-'}\n{preview}"
            )
        await message.answer("直近のフィードバックです：\n" + "\n\n".join(lines))
        return

    if subcommand == "stats":
        days = 7
        if len(parts) >= 3:
            try:
                days = max(1, min(14, int(parts[2])))
            except ValueError:
                await message.answer("日数は数字で指定してください。例: /admin stats 7")
                return
        stats_rows = get_daily_stats(days=days)
        if not stats_rows:
            await message.answer("日次集計を取得できませんでした。")
            return

        today_jst = _usage_today(utcnow()).isoformat()
        stats_by_date = {row["date"]: row for row in stats_rows}
        today_stats = stats_by_date.get(today_jst, stats_rows[0])
        sorted_rows = sorted(stats_rows, key=lambda row: row["date"])
        lines = [
            "📊 Admin stats (JST)",
            (
                f"Today {today_stats['date']}: "
                f"DAU={today_stats.get('dau', 0)} uses={today_stats.get('uses', 0)} "
                f"⭐stars={today_stats.get('stars_sales', 0)} (tx={today_stats.get('payments', 0)}) "
                f"tarot={today_stats.get('tarot', 0)} consult={today_stats.get('consult', 0)} errors={today_stats.get('errors', 0)}"
            ),
            f"---- last {days} days ----",
        ]
        lines.extend(
            [
                (
                    f"{row['date']}: dau={row.get('dau', 0)} uses={row.get('uses', 0)} "
                    f"stars={row.get('stars_sales', 0)} tx={row.get('payments', 0)} "
                    f"tarot={row.get('tarot', 0)} consult={row.get('consult', 0)} errors={row.get('errors', 0)}"
                )
                for row in sorted_rows
            ]
        )
        await message.answer("\n".join(lines))
        return

    if subcommand not in {"grant", "revoke"}:
        await message.answer(
            "現在サポートしているのは grant / revoke / feedback_recent / stats です。"
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
    if not _should_process_message(message, handler="refund"):
        return

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
    lang = get_user_lang_or_default(user_id)
    lang_code = normalize_lang(lang)
    chat_id = get_chat_id(message)
    can_use_bot = hasattr(message, "chat") and getattr(message.chat, "id", None) is not None
    release_inflight = await _acquire_inflight(user_id, message, lang=lang_code)
    event_success = False
    event_error: str | None = None

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
                "label_en": _get_position_label_translation(position.id, "en"),
                "label_pt": _get_position_label_translation(position.id, "pt"),
                "meaning_ja": position.meaning_ja,
                "meaning_en": _get_position_meaning_translation(position.id, "en"),
                "meaning_pt": _get_position_meaning_translation(position.id, "pt"),
                "card": {
                    "id": item.card.id,
                    "name_ja": item.card.name_ja,
                    "name_en": item.card.name_en,
                    "orientation": "reversed" if item.is_reversed else "upright",
                    "orientation_label_ja": orientation_label(item.is_reversed),
                    "orientation_label_en": orientation_label_by_lang(item.is_reversed, "en"),
                    "orientation_label_pt": orientation_label_by_lang(item.is_reversed, "pt"),
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
        lang=lang,
    )

    status_message: Message | None = None
    try:
        status_message = await message.answer(
            t(lang_code, "READING_IN_PROGRESS_NOTICE"),
            reply_markup=build_quick_menu(user_id),
        )
        openai_start = perf_counter()
        try:
            answer, fatal = await call_openai_with_retry(messages, lang=lang_code)
        except TypeError:
            answer, fatal = await call_openai_with_retry(messages)
        openai_latency_ms = (perf_counter() - openai_start) * 1000
        if fatal:
            error_text = (
                answer
                + "\n\n"
                + t(lang_code, "APOLOGY_RETRY_NOTE")
            )
            if can_use_bot and chat_id is not None:
                await send_long_text(
                    chat_id,
                    error_text,
                    reply_to=getattr(message, "message_id", None),
                    reply_markup_first=build_quick_menu(user_id),
                )
            else:
                await message.answer(error_text, reply_markup=build_quick_menu(user_id))
            event_error = "fatal_tarot"
            return

        if spread_to_use.id == THREE_CARD_TIME_AXIS.id:
            base_answer = answer
            if guidance_note:
                base_answer = f"{base_answer}\n\n{guidance_note}"
            base_answer = append_caution_note(user_query, base_answer, lang=lang_code)
            formatted_answer = format_time_axis_tarot_answer(
                base_answer,
                drawn_cards=drawn_payload,
                time_range_text=get_time_range_text(lang_code),
                caution_note=get_caution_note(lang_code),
                lang=lang_code,
                card_line_prefix=get_card_line_prefix(lang_code),
            )
        else:
            formatted_answer = format_long_answer(
                answer,
                "tarot",
                card_line=format_drawn_cards(drawn_payload, lang=lang_code),
                position_labels=spread_to_use.position_labels if lang_code == "ja" else None,
                lang=lang_code,
                card_line_prefix=get_card_line_prefix(lang_code),
            )
            if guidance_note:
                formatted_answer = f"{formatted_answer}\n\n{guidance_note}"
            formatted_answer = append_caution_note(user_query, formatted_answer, lang=lang_code)
            formatted_answer = finalize_tarot_answer(
                formatted_answer,
                card_line_prefix=get_card_line_prefix(lang_code),
                caution_note=get_caution_note(lang_code),
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
        upgrade_markup = build_upgrade_keyboard(lang=lang_code) if spread_to_use.id == ONE_CARD.id else None
        share_markup = build_share_start_keyboard(lang=lang_code)
        final_markup = merge_inline_keyboards(upgrade_markup, share_markup)
        if can_use_bot and chat_id is not None:
            await send_long_text(
                chat_id,
                formatted_answer,
                reply_to=getattr(message, "message_id", None),
                reply_markup_first=build_quick_menu(user_id),
                reply_markup_last=final_markup,
            )
        else:
            await message.answer(
                formatted_answer, reply_markup=final_markup or build_quick_menu(user_id)
            )
        await restore_base_menu(message, user_id, lang_code)
        event_success = True
    except Exception:
        logger.exception("Unexpected error during tarot reading")
        fallback = (
            "占いの準備で少しつまずいてしまいました。\n"
            "時間をおいて、もう一度話しかけてもらえるとうれしいです。"
        )
        if can_use_bot and chat_id is not None:
            await send_long_text(
                chat_id,
                fallback,
                reply_to=getattr(message, "message_id", None),
                reply_markup_first=build_quick_menu(user_id),
            )
        else:
            await message.answer(fallback, reply_markup=build_quick_menu(user_id))
        event_error = "tarot_exception"
    finally:
        await _safe_delete_message(status_message)
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
        _safe_log_app_event(
            event_type="tarot",
            user_id=user_id,
            payload=json.dumps(
                {
                    "spread": spread_to_use.id,
                    "theme": effective_theme,
                    "success": event_success,
                }
            ),
        )
        if event_error:
            _safe_log_app_event(
                event_type="error",
                user_id=user_id,
                payload=event_error,
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
    lang = get_user_lang_or_default(user_id)
    total_start = perf_counter()
    openai_latency_ms: float | None = None
    consult_intent = _is_consult_intent(user_query)
    admin_mode = is_admin_user(user_id)
    chat_id_value = getattr(getattr(message, "chat", None), "id", None)
    can_use_bot = chat_id_value is not None
    user: UserRecord | None = ensure_user(user_id, now=now) if user_id is not None else None
    paywall_triggered = False
    event_success = False
    event_error: str | None = None

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
            full_notice = _should_show_general_chat_full_notice(user, now)
            block_message = _build_consult_block_message(
                trial_active=trial_active, short=not full_notice
            )
            reply_markup = build_store_keyboard(lang=lang) if full_notice else None
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
        user_id, message, busy_message=t(lang, "BUSY_CHAT_MESSAGE"), lang=lang
    )

    try:
        openai_start = perf_counter()
        try:
            answer, fatal = await call_openai_with_retry(
                build_general_chat_messages(user_query, lang=lang), lang=lang
            )
        except TypeError:
            answer, fatal = await call_openai_with_retry(
                build_general_chat_messages(user_query, lang=lang)
            )
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
            event_error = "fatal_consult"
            return
        safe_answer = await ensure_general_chat_safety(answer, lang=lang)
        safe_answer = format_long_answer(safe_answer, "consult", lang=lang)
        safe_answer = append_caution_note(user_query, safe_answer, lang=lang)
        if can_use_bot and chat_id_value is not None:
            await send_long_text(
                chat_id_value,
                safe_answer,
                reply_to=message.message_id,
                reply_markup_first=build_base_menu(user_id),
                reply_markup_last=build_base_menu(user_id),
            )
        else:
            await message.answer(safe_answer, reply_markup=build_base_menu(user_id))
        share_markup = build_share_start_keyboard(lang=lang)
        cta_text = "Share this bot 👇"
        try:
            if can_use_bot and chat_id_value is not None:
                await bot.send_message(
                    chat_id_value,
                    cta_text,
                    reply_to_message_id=message.message_id,
                    reply_markup=share_markup,
                )
            else:
                await message.answer(cta_text, reply_markup=share_markup)
        except Exception:
            await message.answer(cta_text, reply_markup=share_markup)
        event_success = True
    except Exception:
        logger.exception("Unexpected error during general chat")
        fallback = (
            "すみません、今ちょっと調子が悪いみたいです…\n"
            "少し時間をおいてから、もう一度メッセージを送ってもらえると助かります。"
        )
        await message.answer(fallback)
        event_error = "consult_exception"
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
        _safe_log_app_event(
            event_type="consult",
            user_id=user_id,
            payload=json.dumps({"success": event_success, "intent": "consult" if consult_intent else "general"}),
        )
        if event_error:
            _safe_log_app_event(
                event_type="error",
                user_id=user_id,
                payload=event_error,
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
            "feedback",
            "admin",
        ]
    )
)
async def handle_message(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    lang = get_user_lang_or_default(user_id)
    content_type = getattr(message, "content_type", ContentType.TEXT)
    is_text = content_type == ContentType.TEXT
    if not is_text:
        ok, error_message = validate_question_text(None, is_text=False, lang=lang)
        if not ok and error_message:
            await message.answer(error_message, reply_markup=build_base_menu(user_id))
        return

    text = (message.text or "").strip()
    is_language_button, normalized_language_hint = is_language_reply_button(text)
    now = utcnow()
    if not _should_process_message(
        message,
        handler="router",
        allow_language_duplicate=is_language_button,
        language_button_hint=normalized_language_hint,
    ):
        return
    if await reset_state_if_inactive(message, now=now):
        return
    mark_user_active(user_id, now=now)
    lang = get_user_lang_or_default(user_id)
    menu_markup = build_base_menu(user_id)
    quick_menu = build_quick_menu(user_id)
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
            t(lang, "ASK_FOR_MORE_DETAIL"),
            reply_markup=menu_markup,
        )
        return

    if text.startswith("🎩"):
        await prompt_tarot_mode(message)
        return

    if text.startswith("💬"):
        await prompt_consult_mode(message)
        return

    if text.startswith("🛒"):
        await prompt_charge_menu(message)
        return

    if text.startswith("📊"):
        await prompt_status(message, now=now)
        return

    if is_language_button:
        await cmd_lang(message, skip_dedup=True)
        return

    spread_from_command, cleaned = parse_spread_command(text)

    if spread_from_command:
        set_user_mode(user_id, "tarot")
        if text.lower().startswith("/love1"):
            set_tarot_theme(user_id, "love")
        user_query = cleaned or t(lang, "DEFAULT_TAROT_QUERY_FALLBACK")
        await execute_tarot_request(
            message,
            user_query=user_query,
            spread=spread_from_command,
            theme=get_tarot_theme(user_id),
        )
        return

    if tarot_flow == "awaiting_theme":
        await message.answer(
            t(lang, "TAROT_THEME_PROMPT"), reply_markup=build_tarot_theme_keyboard(lang=lang)
        )
        return

    if tarot_flow == "awaiting_question":
        ok, error_message = validate_question_text(text, is_text=is_text, lang=lang)
        if not ok and error_message:
            await message.answer(error_message, reply_markup=quick_menu)
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
        ok, error_message = validate_question_text(text, is_text=is_text, lang=lang)
        if not ok and error_message:
            await message.answer(error_message, reply_markup=quick_menu)
            return
        set_user_mode(user_id, "tarot")
        await execute_tarot_request(
            message,
            user_query=text,
            spread=ONE_CARD,
            theme=tarot_theme,
        )
        return

    ok, error_message = validate_question_text(text, is_text=is_text, lang=lang)
    if not ok and error_message:
        await message.answer(error_message, reply_markup=quick_menu)
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
