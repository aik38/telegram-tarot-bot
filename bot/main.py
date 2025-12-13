import asyncio
import logging
import random
from typing import Tuple

from aiogram import Bot, Dispatcher, F
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


bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
client = OpenAI(api_key=OPENAI_API_KEY)

logger = logging.getLogger(__name__)


def categorize_question(text: str) -> str:
    lowered = text.lower()
    categories = {
        "恋愛": ["恋愛", "彼氏", "彼女", "片思い", "結婚", "離婚", "パートナー", "恋人"],
        "仕事": ["仕事", "転職", "会社", "上司", "同僚", "キャリア", "職場", "昇進"],
        "金運": ["お金", "収入", "貯金", "投資", "ビジネス", "副業", "金運", "財"],
        "全体運": ["今日", "明日", "1日", "運勢", "ラッキー", "全体", "1 日", "今週"],
    }

    for category, keywords in categories.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return category
    return "その他"


def build_system_prompt(category: str) -> str:
    # 返答トーンのガイドラインを system メッセージに含め、
    # 「優しく・断定しない・選択肢を提案する」スタンスを徹底する。
    tone_guide = (
        "# 返答トーンのガイドライン\n"
        "- 優しく、フレンドリーだが馴れ馴れしすぎない。\n"
        "- 「絶対」「必ず」を避け、「可能性」「かもしれません」を使う。\n"
        "- まず相談者の気持ちを受け止めてからカード結果を伝える。\n"
        "- 行動を強要せず、複数の選択肢や提案を示す。\n"
    )

    common = (
        "あなたは優しい日本語で占うタロット占い師です。"
        "カードの結果は断定せず、相談者の気持ちを尊重して伝えてください。"
        "スプレッドやカード名は必要に応じて簡潔に触れ、日常生活で活かせる提案を添えます。"
    )

    category_prompts = {
        "恋愛": "恋愛やパートナーシップについて、感情面に寄り添いながら前向きなヒントを伝えてください。",
        "仕事": "仕事やキャリアの相談では、現実的で実行しやすいアドバイスを意識してください。",
        "金運": "お金や収入の相談では、無理のない工夫やリスクへの注意喚起を優しく添えてください。",
        "全体運": "全体運や今日・明日の運勢では、日常で試しやすい小さな行動の提案を添えてください。",
        "その他": "相談内容に合わせて、心を整えるヒントや次の一歩を優しく提案してください。",
    }

    return f"{tone_guide}\n{common}{category_prompts.get(category, '')}"


async def call_openai_with_retry(user_text: str, category: str) -> Tuple[str, bool]:
    system_prompt = build_system_prompt(category)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text},
    ]

    max_attempts = 3
    base_delay = 1.5

    for attempt in range(1, max_attempts + 1):
        try:
            completion = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini", messages=messages
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
        "・『最近、何となく気持ちが落ち着きません』\n\n"
        "◆ やさしいお願い\n"
        "医療・法律・投資の判断は専門家に相談してください。\n"
        "占いは心の整理と気づきのヒントで、結果を保証するものではありません。\n"
        "不安が強いときは無理に信じすぎず、自分を大切にしてくださいね。"
    )


@dp.message(F.text)
async def handle_question(message: Message) -> None:
    user_text = (message.text or "").strip()
    if not user_text:
        await message.answer(
            "気になることをもう少し詳しく教えてくれるとうれしいです。"
        )
        return

    category = categorize_question(user_text)

    try:
        answer, fatal = await call_openai_with_retry(user_text, category)
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

    await message.answer(answer)


async def main() -> None:
    setup_logging()
    logger.info("Starting akolasia_tarot_bot")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
