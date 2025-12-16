import asyncio
import json
import logging
import random
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

from core.config import OPENAI_API_KEY, TELEGRAM_BOT_TOKEN
from core.db import (
    TicketColumn,
    UserRecord,
    consume_ticket,
    ensure_user,
    get_user,
    grant_purchase,
    log_payment,
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
    "/love3": THREE_CARD_SITUATION,
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


def build_paid_hint(text: str) -> str | None:
    hints = ["3枚", "３枚", "三枚", "3card", "3 カード", "ヘキサ", "ケルト", "十字", "7枚", "７枚", "10枚", "１０枚"]
    if any(hint in text for hint in hints):
        return "3枚以上のスプレッドはコマンド指定で受け付けています：/love3 /hexa /celtic（無料は1枚引きです：/love1）。"
    return None


def consume_ticket_for_spread(user_id: int, spread: Spread) -> bool:
    column = SPREAD_TICKET_COLUMNS.get(spread.id)
    if not column:
        return False
    return consume_ticket(user_id, ticket=column)


def format_status(user: UserRecord) -> str:
    premium_until = user.premium_until.isoformat(sep=" ") if user.premium_until else "なし"
    return (
        "現在のご利用状況です。\n"
        f"・有効期限つきパス: {premium_until}\n"
        f"・3枚チケット: {user.tickets_3}枚\n"
        f"・7枚チケット: {user.tickets_7}枚\n"
        f"・10枚チケット: {user.tickets_10}枚\n"
        f"・画像オプション: {'有効' if user.images_enabled else '無効'}"
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
    *, spread: Spread, user_query: str, drawn_cards: list[dict[str, str]]
) -> list[dict[str, str]]:
    rules_text = "\n".join(f"- {rule}" for rule in TAROT_OUTPUT_RULES)
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


def build_store_keyboard() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for product in iter_products():
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{product.title} - {product.price_stars}⭐️", callback_data=f"buy:{product.sku}"
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("buy"))
async def cmd_buy(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is not None:
        ensure_user(user_id)

    await message.answer(
        "ご利用ありがとうございます。ご希望の商品を選んでください。\n"
        "Stars (XTR) 決済に対応しています。",
        reply_markup=build_store_keyboard(),
    )


@dp.message(Command("status"))
async def cmd_status(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is None:
        await message.answer("ユーザー情報を確認できませんでした。個別チャットからお試しくださいませ。")
        return

    user = get_user_with_default(user_id) or ensure_user(user_id)
    status = format_status(user)
    await message.answer(status)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "こんにちは、AIタロット占いボットの akolasia_tarot_bot です🌿\n"
        "ゆったりと心を整えながら、気になることをお話しくださいね。\n\n"
        "◆ 相談できるメニュー\n"
        "・恋愛運の占い（片思い、結婚のタイミングなど）\n"
        "・仕事や転職の占い（職場の人間関係も歓迎）\n"
        "・金運やお金にまつわる相談\n"
        "・今日 / 明日の運勢や全体運\n"
        "・テーマがまとまっていなくても、感じていることをそのまま話してOKです\n\n"
        "◆ 使い方の例\n"
        "・『今の恋愛はこの先どうなりますか？』\n"
        "・『明日の恋人の機嫌はどうかな？』\n"
        "・『転職した方が良いか迷っています』\n"
        "・『最近、何となく気持ちが落ち着きません』\n"
        "・『占って』とメッセージに入れるとタロット占いモードになります（1枚引き）\n"
        "・複数枚スプレッドはコマンドで指定してください：/love3 /hexa /celtic（無料は /love1）\n"
        "・それ以外のメッセージには、いつもの雑談や相談相手としてお話しします\n\n"
        "◆ やさしいお願い\n"
        "医療・法律・投資の判断は専門家に相談してください。\n"
        "占いは心の整理と気づきのヒントで、結果を保証するものではありません。\n"
        "不安が強いときは無理に信じすぎず、自分を大切にしてくださいね。",
    )


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
    log_payment(
        user_id=user_id,
        sku=product.sku,
        stars=payment.total_amount,
        telegram_payment_charge_id=payment.telegram_payment_charge_id,
        provider_payment_charge_id=payment.provider_payment_charge_id,
    )
    updated_user = grant_purchase(user_id, product.sku)
    unlock_message = build_unlock_text(product, updated_user)
    await message.answer(
        f"{product.title}のご購入ありがとうございました！\n{unlock_message}\n"
        "いつでも /status でご利用状況を確認いただけます。"
    )


async def handle_tarot_reading(
    message: Message,
    user_query: str,
    *,
    spread: Spread | None = None,
    guidance_note: str | None = None,
) -> None:
    logger.info(
        "Handling message",
        extra={
            "mode": "tarot",
            "user_id": message.from_user.id if message.from_user else None,
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


async def handle_general_chat(message: Message, user_query: str) -> None:
    logger.info(
        "Handling message",
        extra={
            "mode": "chat",
            "user_id": message.from_user.id if message.from_user else None,
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

    if text.startswith("/start"):
        return

    if not text:
        await message.answer(
            "気になることをもう少し詳しく教えてくれるとうれしいです。"
        )
        return

    spread_from_command, cleaned = parse_spread_command(text)
    user_id = message.from_user.id if message.from_user else None

    if spread_from_command:
        if user_id is not None:
            ensure_user(user_id)

        if PAYWALL_ENABLED and is_paid_spread(spread_from_command):
            if not is_premium_user(user_id):
                if user_id is None or not consume_ticket_for_spread(user_id, spread_from_command):
                    await message.answer(
                        "こちらは有料メニューです。\n"
                        "ご購入は /buy からお進みいただけます（無料の1枚引きは /love1 でお楽しみください）。"
                    )
                    return

        user_query = cleaned or "恋愛について占ってください。"
        await handle_tarot_reading(
            message,
            user_query=user_query,
            spread=spread_from_command,
        )
        return

    if is_tarot_request(text):
        guidance_note = build_paid_hint(text)
        await handle_tarot_reading(
            message,
            user_query=text,
            guidance_note=guidance_note,
        )
    else:
        await handle_general_chat(message, user_query=text)


async def main() -> None:
    setup_logging()
    logger.info("Starting akolasia_tarot_bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
