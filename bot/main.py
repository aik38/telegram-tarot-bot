import asyncio
import json
import logging
import os
import random
from datetime import datetime, time, timedelta, timezone
from typing import Iterable

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    CallbackQuery,
)
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

from core.config import ADMIN_USER_IDS, OPENAI_API_KEY, SUPPORT_EMAIL, TELEGRAM_BOT_TOKEN
from core.db import (
    TicketColumn,
    UserRecord,
    consume_ticket,
    ensure_user,
    get_payment_by_charge_id,
    get_user,
    grant_purchase,
    has_accepted_terms,
    has_active_pass,
    increment_general_chat_count,
    increment_one_oracle_count,
    log_payment,
    mark_payment_refunded,
    set_terms_accepted,
    set_last_general_chat_block_notice,
    USAGE_TIMEZONE,
)
from core.monetization import PAYWALL_ENABLED, get_user_with_default, is_premium_user
from core.logging import setup_logging
from core.prompts import CHAT_SYSTEM_PROMPT, TAROT_OUTPUT_RULES, TAROT_SYSTEM_PROMPT
from core.tarot import (
    ONE_CARD,
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

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)

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
    "ください。購入は /buy です。"
)
GENERAL_CHAT_BLOCK_NOTICE_COOLDOWN = timedelta(hours=1)


def _usage_today(now: datetime) -> datetime.date:
    return now.astimezone(USAGE_TIMEZONE).date()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_general_chat_messages(user_query: str) -> list[dict[str, str]]:
    """通常チャットモードの system prompt を組み立てる。"""
    return [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
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
            return answer, False
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


COMMAND_SPREAD_MAP: dict[str, Spread] = {
    "/love1": ONE_CARD,
    "/read1": ONE_CARD,
    "/love3": THREE_CARD_SITUATION,
    "/read3": THREE_CARD_SITUATION,
    "/hexa": HEXAGRAM,
    "/celtic": CELTIC_CROSS,
}


PAID_SPREAD_IDS: set[str] = {THREE_CARD_SITUATION.id, HEXAGRAM.id, CELTIC_CROSS.id}

SPREAD_TICKET_COLUMNS: dict[str, TicketColumn] = {
    THREE_CARD_SITUATION.id: "tickets_3",
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
    has_pass = is_premium_user(user_id, now=now)
    date_key = _usage_today(now).isoformat()
    memory_key = (user_id, date_key)
    base_count = ONE_ORACLE_MEMORY.get(memory_key, latest_user.one_oracle_count_today)

    limit = (
        FREE_ONE_ORACLE_TRIAL_PER_DAY
        if _is_in_general_chat_trial(latest_user, now)
        else FREE_ONE_ORACLE_POST_TRIAL_PER_DAY
    )

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


def get_start_text() -> str:
    bot_name = get_bot_display_name()
    return (
        f"こんにちは、AIタロット占いボット {bot_name} です🌿\n"
        "無料でお試しいただける回数と、パスで解放される相談チャットをご案内します。\n\n"
        "【タロット占い】\n"
        "・ワンオラクル：/read1 または『〇〇 占って』で1枚（初回5日間は1日2回、6日目以降は1日1回無料。無料分はショート回答）\n"
        "・複数枚スプレッド：/read3 /hexa /celtic（有料）\n"
        "・恋愛専用：/love1 /love3\n"
        "・『〇〇 占って』でワンオラクルへお任せいただけます。\n\n"
        "【相談チャット】\n"
        "・メッセージ先頭に『相談:』と添えるとスムーズです。\n"
        "・初回5日間は1日2通まで無料でご相談いただけます。\n"
        "・6日目以降は7日/30日パスご購入で回数無制限になります。\n\n"
        "【購入・確認】\n"
        "/buy    おすすめメニューとStars決済（相談したい方はパスがおすすめ）\n"
        "/status trial日数・無料残数・パス期限を確認\n\n"
        "【サポートと規約】\n"
        "/terms      利用規約\n"
        "/support    お問い合わせ\n"
        "/paysupport 決済トラブル\n"
        "医療・法律・投資は専門家にご相談ください。"
    )


def get_store_intro_text() -> str:
    return (
        "ご利用ありがとうございます。お悩みに合わせてお選びください。\n"
        "・迷ったら：スリーカード(3枚)かケルト十字(10枚)でじっくり整理\n"
        "・相談重視：7日/30日パスで相談チャットを解放\n"
        "・決済はTelegram Stars (XTR) です。ゆっくりお進みください。\n"
        "・価格（⭐️）は各メニューのボタンに表示されています。\n"
        "・選択すると購入確認が表示されます。"
    )


def consume_ticket_for_spread(user_id: int, spread: Spread) -> bool:
    column = SPREAD_TICKET_COLUMNS.get(spread.id)
    if not column:
        return False
    return consume_ticket(user_id, ticket=column)


def format_status(user: UserRecord, *, now: datetime | None = None) -> str:
    now = now or utcnow()
    pass_until = user.pass_until or user.premium_until
    has_pass = has_active_pass(user.user_id, now=now)
    status_title = "現在のご利用状況です。"
    if is_admin_user(user.user_id):
        status_title = "現在のご利用状況（管理者モード）です。"
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
    else:
        pass_label = "なし"

    next_reset = datetime.combine(
        _usage_today(now) + timedelta(days=1), time(0, 0), tzinfo=USAGE_TIMEZONE
    )

    return (
        f"{status_title}\n"
        f"・trial: 初回利用から{trial_day}日目\n"
        f"・パス有効期限: {pass_label}\n"
        f"・ワンオラクル無料枠: 1日{one_oracle_limit}回（本日の残り {one_remaining} 回）\n"
        f"・相談チャット: {general_line}\n"
        f"・3枚チケット: {user.tickets_3}枚\n"
        f"・7枚チケット: {user.tickets_7}枚\n"
        f"・10枚チケット: {user.tickets_10}枚\n"
        f"・画像オプション: {'有効' if user.images_enabled else '無効'}\n"
        f"・次回リセット: {next_reset.strftime('%m/%d %H:%M JST')}"
    )


def build_unlock_text(product: Product, user: UserRecord) -> str:
    if product.sku in TICKET_SKU_TO_COLUMN:
        column = TICKET_SKU_TO_COLUMN[product.sku]
        balance = getattr(user, column)
        return f"{product.title}を追加しました。現在の残り枚数は {balance} 枚です。"

    if product.sku.startswith("PASS_"):
        until = user.premium_until.isoformat(sep=" ") if user.premium_until else "有効期限を更新しました。"
        duration = "7日間" if product.sku == "PASS_7D" else "30日間"
        return (
            f"{duration}のパスをご利用いただけます。\n"
            f"現在の有効期限: {until}"
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
) -> list[dict[str, str]]:
    rules = SHORT_TAROT_OUTPUT_RULES if short else TAROT_OUTPUT_RULES
    rules_text = "\n".join(f"- {rule}" for rule in rules)
    tarot_system_prompt = f"{TAROT_SYSTEM_PROMPT}\n出力ルール:\n{rules_text}"

    tarot_payload = {
        "spread_id": spread.id,
        "spread_name_ja": spread.name_ja,
        "positions": drawn_cards,
        "user_question": user_query,
    }

    return [
        {"role": "system", "content": tarot_system_prompt},
        {"role": "assistant", "content": json.dumps(tarot_payload, ensure_ascii=False, indent=2)},
        {"role": "user", "content": user_query},
    ]


def format_drawn_card_heading(drawn_cards: list[dict[str, str]]) -> str:
    if not drawn_cards:
        return "引いたカードをお知らせできませんでした。"

    if len(drawn_cards) == 1:
        card = drawn_cards[0]["card"]
        card_label = f"{card['name_ja']}（{card['orientation_label_ja']}）"
        return f"引いたカードは「{card_label}」です。"

    lines = ["引いたカード："]
    for index, item in enumerate(drawn_cards, start=1):
        card = item["card"]
        card_label = f"{card['name_ja']}（{card['orientation_label_ja']}）"
        lines.append(f"{index}. {card_label} - {item['label_ja']}")
    return "\n".join(lines)


def ensure_tarot_response_prefixed(answer: str, heading: str) -> str:
    if answer.lstrip().startswith("引いたカード"):
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
TERMS_CALLBACK_AGREE_AND_BUY = "terms:agree_buy"


def get_terms_text() -> str:
    support_email = get_support_email()
    return (
        "利用規約（抜粋）\n"
        "・18歳以上の自己責任で利用してください。\n"
        "・医療/法律/投資など専門判断は提供しません。\n"
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
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="同意する", callback_data=TERMS_CALLBACK_AGREE)]
    ]

    if include_buy_option:
        rows.append(
            [
                InlineKeyboardButton(
                    text="同意して購入へ進む", callback_data=TERMS_CALLBACK_AGREE_AND_BUY
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_terms_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="利用規約を確認", callback_data=TERMS_CALLBACK_SHOW)],
            [
                InlineKeyboardButton(
                    text="同意して購入へ進む", callback_data=TERMS_CALLBACK_AGREE_AND_BUY
                )
            ],
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


async def send_store_menu(message: Message) -> None:
    await message.answer(
        get_store_intro_text(), reply_markup=build_store_keyboard()
    )


@dp.message(Command("terms"))
async def cmd_terms(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is not None:
        ensure_user(user_id)

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip().lower() == "agree" and user_id is not None:
        set_terms_accepted(user_id)
        await message.answer("利用規約への同意を記録しました。/buy からご購入いただけます。")
        return

    await message.answer(
        get_terms_text(), reply_markup=build_terms_keyboard(include_buy_option=True)
    )


@dp.callback_query(F.data == TERMS_CALLBACK_SHOW)
async def handle_terms_show(query: CallbackQuery):
    await query.answer()
    if query.message:
        await query.message.answer(
            get_terms_text(), reply_markup=build_terms_prompt_keyboard()
        )


@dp.callback_query(F.data == TERMS_CALLBACK_AGREE)
async def handle_terms_agree(query: CallbackQuery):
    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await query.answer("ユーザー情報を確認できませんでした。", show_alert=True)
        return

    set_terms_accepted(user_id)
    await query.answer("同意を記録しました。", show_alert=True)
    if query.message:
        await query.message.answer(
            "利用規約への同意を記録しました。/buy から購入手続きに進めます。"
        )


@dp.callback_query(F.data == TERMS_CALLBACK_AGREE_AND_BUY)
async def handle_terms_agree_and_buy(query: CallbackQuery):
    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await query.answer("ユーザー情報を確認できませんでした。", show_alert=True)
        return

    ensure_user(user_id)
    set_terms_accepted(user_id)
    await query.answer("同意を記録しました。", show_alert=True)
    if query.message:
        await send_store_menu(query.message)


@dp.message(Command("support"))
async def cmd_support(message: Message) -> None:
    await message.answer(get_support_text())


@dp.message(Command("paysupport"))
async def cmd_pay_support(message: Message) -> None:
    await message.answer(get_pay_support_text())


@dp.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is not None:
        ensure_user(user_id)
        if not has_accepted_terms(user_id):
            await message.answer(
                f"{TERMS_PROMPT_BEFORE_BUY}\n/terms から同意をお願いします。",
                reply_markup=build_terms_prompt_keyboard(),
            )
            return

    await send_store_menu(message)


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        await message.answer("ユーザー情報を確認できませんでした。個別チャットからお試しくださいませ。")
        return

    now = utcnow()
    user = get_user_with_default(user_id) or ensure_user(user_id, now=now)
    status = format_status(user, now=now)
    await message.answer(status)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(get_start_text())


@dp.callback_query(F.data.startswith("buy:"))
async def handle_buy_callback(query: CallbackQuery):
    data = query.data or ""
    sku = data.split(":", maxsplit=1)[1] if ":" in data else None
    product = get_product(sku) if sku else None
    if not product:
        await query.answer("商品情報を取得できませんでした。少し時間をおいてお試しください。", show_alert=True)
        return

    user_id = query.from_user.id if query.from_user else None
    if user_id is None:
        await query.answer("ユーザーを特定できませんでした。個別チャットからお試しください。", show_alert=True)
        return

    ensure_user(user_id)
    if product.sku == "ADDON_IMAGES" and not IMAGE_ADDON_ENABLED:
        await query.answer("画像追加オプションは準備中です。リリースまでお待ちください。", show_alert=True)
        return
    if not has_accepted_terms(user_id):
        await query.answer(TERMS_PROMPT_BEFORE_BUY, show_alert=True)
        if query.message:
            await query.message.answer(
                f"{TERMS_PROMPT_BEFORE_BUY}\n/terms から同意をお願いします。",
                reply_markup=build_terms_prompt_keyboard(),
            )
        return
    payload = json.dumps({"sku": product.sku, "user_id": user_id})
    prices = [LabeledPrice(label=product.title, amount=product.price_stars)]

    if query.message:
        await query.message.answer_invoice(
            title=product.title,
            description=product.description,
            payload=payload,
            provider_token="",
            currency="XTR",
            prices=prices,
        )
    await query.answer("お支払い画面を開きます。ゆっくり進めてくださいね。")


@dp.callback_query(F.data == "addon:pending")
async def handle_addon_pending(query: CallbackQuery):
    await query.answer("画像追加オプションは準備中です。もう少しお待ちください。", show_alert=True)


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    payload_data: dict[str, object]
    try:
        payload_data = json.loads(payment.invoice_payload)
    except json.JSONDecodeError:
        payload_data = {}

    sku = payload_data.get("sku") if isinstance(payload_data, dict) else None
    user_id_payload = payload_data.get("user_id") if isinstance(payload_data, dict) else None
    product = get_product(str(sku)) if sku else None
    user_id = (
        int(user_id_payload)
        if isinstance(user_id_payload, (str, int))
        else (message.from_user.id if message.from_user else None)
    )

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
    if not created:
        await message.answer(
            "このお支払いはすでに処理済みです。/status から利用状況をご確認ください。"
        )
        return
    updated_user = grant_purchase(user_id, product.sku)
    unlock_message = build_unlock_text(product, updated_user)
    await message.answer(
        f"{product.title}のご購入ありがとうございました！\n{unlock_message}\n"
        "いつでも /status でご利用状況を確認いただけます。"
    )


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
) -> None:
    logger.info(
        "Handling message",
        extra={
            "mode": "tarot",
            "user_id": message.from_user.id if message.from_user else None,
            "admin_mode": is_admin_user(message.from_user.id if message.from_user else None),
            "text_preview": _preview_text(user_query),
        },
    )

    spread_to_use = spread or choose_spread(user_query)
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

    heading = format_drawn_card_heading(drawn_payload)
    messages = build_tarot_messages(
        spread=spread_to_use,
        user_query=user_query,
        drawn_cards=drawn_payload,
        short=short_response,
    )

    try:
        answer, fatal = await call_openai_with_retry(messages)
    except Exception:
        logger.exception("Unexpected error during tarot reading")
        await message.answer(
            "占いの準備で少しつまずいてしまいました。\n"
            "時間をおいて、もう一度話しかけてもらえるとうれしいです。"
        )
        return

    if fatal:
        await message.answer(
            answer
            + "\n\nご不便をおかけしてごめんなさい。時間をおいて再度お試しください。"
        )
        return

    safe_answer = ensure_tarot_response_prefixed(answer, heading)
    if guidance_note:
        safe_answer = f"{safe_answer}\n\n{guidance_note}"
    await message.answer(safe_answer)


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
    consult_intent = _is_consult_intent(user_query)
    admin_mode = is_admin_user(user_id)
    user: UserRecord | None = ensure_user(user_id, now=now) if user_id is not None else None

    if user is not None and not admin_mode:
        trial_active = _is_in_general_chat_trial(user, now)
        out_of_quota = user.general_chat_count_today >= FREE_GENERAL_CHAT_PER_DAY
        has_pass = has_active_pass(user_id, now=now)

        if (trial_active and out_of_quota) or (not trial_active and not has_pass):
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

        increment_general_chat_count(user_id, now=now)

    logger.info(
        "Handling message",
        extra={
            "mode": "chat",
            "user_id": message.from_user.id if message.from_user else None,
            "admin_mode": admin_mode,
            "text_preview": _preview_text(user_query),
        },
    )

    try:
        answer, fatal = await call_openai_with_retry(build_general_chat_messages(user_query))
        if fatal:
            await message.answer(
                answer
                + "\n\nご不便をおかけしてごめんなさい。時間をおいて再度お試しください。"
            )
            return
        safe_answer = await ensure_general_chat_safety(answer)
        await message.answer(safe_answer)
    except Exception:
        logger.exception("Unexpected error during general chat")
        await message.answer(
            "すみません、今ちょっと調子が悪いみたいです…\n"
            "少し時間をおいてから、もう一度メッセージを送ってもらえると助かります。"
        )


@dp.message()
async def handle_message(message: Message) -> None:
    text = (message.text or "").strip()
    now = utcnow()
    user_id = message.from_user.id if message.from_user else None
    admin_mode = is_admin_user(user_id)
    user: UserRecord | None = None

    logger.info(
        "Received message",
        extra={
            "mode": "router",
            "user_id": user_id,
            "admin_mode": admin_mode,
            "text_preview": _preview_text(text),
        },
    )

    if text.startswith("/start"):
        return

    if not text:
        await message.answer(
            "気になることをもう少し詳しく教えてくれるとうれしいです。"
        )
        return
    spread_from_command, cleaned = parse_spread_command(text)

    if spread_from_command:
        short_response = False
        if user_id is not None:
            user = ensure_user(user_id, now=now)

        if PAYWALL_ENABLED and is_paid_spread(spread_from_command):
            if not is_premium_user(user_id, now=now):
                if user_id is None or not consume_ticket_for_spread(user_id, spread_from_command):
                    await message.answer(
                        "こちらは有料メニューです。\n"
                        "ご購入は /buy からお進みいただけます（無料の1枚引きは /read1 または『占って』でお楽しみください）。"
                    )
                    return

        if (
            spread_from_command == ONE_CARD
            and user_id is not None
            and user is not None
            and not admin_mode
        ):
            allowed, short_response, user = _evaluate_one_oracle_access(
                user=user, user_id=user_id, now=now
            )
            if not allowed:
                await message.answer(
                    "ワンオラクルの無料枠は本日分を使い切りました（trial中:1日2回 / 6日目以降:1日1回）。"
                    "複数枚スプレッドやパスは /buy からご利用いただけます。",
                )
                return

        user_query = cleaned or "今気になっていることについて占ってください。"
        await handle_tarot_reading(
            message,
            user_query=user_query,
            spread=spread_from_command,
            short_response=short_response,
        )
        return

    if is_tarot_request(text):
        short_response = False
        if user_id is not None:
            user = ensure_user(user_id, now=now)
            if not admin_mode:
                allowed, short_response, user = _evaluate_one_oracle_access(
                    user=user, user_id=user_id, now=now
                )
                if not allowed:
                    await message.answer(
                        "ワンオラクルの無料枠は本日分を使い切りました（trial中:1日2回 / 6日目以降:1日1回）。"
                        "複数枚スプレッドやパスは /buy からご利用いただけます。",
                    )
                    return
        else:
            user = None
        guidance_note = build_paid_hint(text)
        await handle_tarot_reading(
            message,
            user_query=text,
            guidance_note=guidance_note,
            short_response=short_response,
        )
    else:
        await handle_general_chat(message, user_query=text)


async def main() -> None:
    setup_logging()
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


