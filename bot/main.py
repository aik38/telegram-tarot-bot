import asyncio
import json
import logging
import random
from typing import Iterable

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
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
from core.logging import setup_logging
from core.prompts import CHAT_SYSTEM_PROMPT, TAROT_OUTPUT_RULES, TAROT_SYSTEM_PROMPT
from core.tarot import (
    ONE_CARD,
    THREE_CARD_SITUATION,
    contains_tarot_like,
    draw_cards,
    is_tarot_request,
    orientation_label,
    strip_tarot_sentences,
)
from core.tarot.spreads import Spread


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


def choose_spread(user_query: str) -> Spread:
    hints = ["3枚", "３枚", "三枚", "3card", "3 カード"]
    if any(hint in user_query for hint in hints):
        return THREE_CARD_SITUATION
    return ONE_CARD


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
        "・『占って』とメッセージに入れるとタロット占いモードになります\n"
        "・それ以外のメッセージには、いつもの雑談や相談相手としてお話しします\n\n"
        "◆ やさしいお願い\n"
        "医療・法律・投資の判断は専門家に相談してください。\n"
        "占いは心の整理と気づきのヒントで、結果を保証するものではありません。\n"
        "不安が強いときは無理に信じすぎず、自分を大切にしてくださいね。",
    )


async def handle_tarot_reading(message: Message, user_query: str) -> None:
    logger.info(
        "Handling message",
        extra={
            "mode": "tarot",
            "user_id": message.from_user.id if message.from_user else None,
            "text_preview": _preview_text(user_query),
        },
    )

    spread = choose_spread(user_query)
    rng = random.Random()
    drawn = draw_cards(spread, rng=rng)

    drawn_payload: list[dict[str, str]] = []
    position_lookup = {pos.id: pos for pos in spread.positions}
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
        spread=spread,
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

    if is_tarot_request(text):
        await handle_tarot_reading(message, user_query=text)
    else:
        await handle_general_chat(message, user_query=text)


async def main() -> None:
    setup_logging()
    logger.info("Starting akolasia_tarot_bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
