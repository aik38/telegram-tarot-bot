from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class SpreadPosition:
    id: str
    label_ja: str
    meaning_ja: str


@dataclass(frozen=True)
class Spread:
    id: str
    name_ja: str
    positions: Sequence[SpreadPosition]
    position_labels: Sequence[str] | None = None


ONE_CARD = Spread(
    id="one_card",
    name_ja="1枚引き",
    positions=[
        SpreadPosition(
            id="main",
            label_ja="メインメッセージ",
            meaning_ja="質問者へのメインメッセージを示します。",
        ),
    ],
    position_labels=("メインメッセージ",),
)

THREE_CARD_SITUATION = Spread(
    id="three_card_situation",
    name_ja="3枚引き（状況・障害・未来）",
    positions=[
        SpreadPosition("situation", "現在の状況", "いまの状況・前提を表します。"),
        SpreadPosition("obstacle", "障害や課題", "乗り越えるべき障害や課題を表します。"),
        SpreadPosition("future", "未来の可能性", "流れの先にある可能性を表します。"),
    ],
    position_labels=("現在", "障害", "未来"),
)

HEXAGRAM = Spread(
    id="hexagram",
    name_ja="ヘキサグラム（7枚恋愛スプレッド）",
    positions=[
        SpreadPosition(
            "your_feelings",
            "あなたの気持ち",
            "あなた自身の本音やいま抱いている感情の流れを示します。",
        ),
        SpreadPosition(
            "partner_feelings",
            "相手の気持ち",
            "お相手の本音や、あなたに対する感情の向き・強さを表します。",
        ),
        SpreadPosition(
            "current_situation",
            "現状",
            "現在の関係性や周囲の状況、二人を取り巻く空気感を読み解きます。",
        ),
        SpreadPosition(
            "obstacle",
            "障害",
            "距離を生んでいる原因、すれ違いの要因、心の壁などの課題を示します。",
        ),
        SpreadPosition(
            "near_future",
            "近未来",
            "これからしばらくの流れや変化の兆しを示し、進展のポイントを示唆します。",
        ),
        SpreadPosition(
            "advice",
            "アドバイス",
            "よりよい未来のためにあなたが取れる行動や心構えを示します。",
        ),
        SpreadPosition(
            "outcome",
            "結果",
            "この流れが続いた先に期待できる結果や関係の着地点を示します。",
        ),
    ],
    position_labels=(
        "あなたの気持ち",
        "相手の気持ち",
        "現状",
        "障害",
        "近未来",
        "アドバイス",
        "結果",
    ),
)

CELTIC_CROSS = Spread(
    id="celtic_cross",
    name_ja="ケルト十字（10枚スプレッド）",
    positions=[
        SpreadPosition("present", "現在（中心テーマ）", "いま直面している主題や状況の中心を示します。"),
        SpreadPosition("challenge", "障害／課題", "乗り越えるべき障害や、現在感じている停滞の要因を表します。"),
        SpreadPosition("conscious", "顕在意識", "あなたが自覚している考え、意識している目的や願望を示します。"),
        SpreadPosition("subconscious", "潜在意識", "自覚しきれていない本音や、深層心理が求めている方向性を示します。"),
        SpreadPosition("past", "過去（原因）", "現状につながる背景や、これまでの影響・原因を表します。"),
        SpreadPosition("near_future", "近い未来", "間もなく訪れる展開や変化の兆しを示します。"),
        SpreadPosition(
            "self_position",
            "助言（あなたの立ち位置）",
            "状況への関わり方や、取るべき姿勢・スタンスへのヒントを示します。",
        ),
        SpreadPosition("environment", "周囲の影響", "周囲の人々や環境がもたらす影響、サポートや制約を表します。"),
        SpreadPosition("hopes_fears", "願望／恐れ", "叶えたいこと、同時に避けたいことなど、心の奥にある期待や不安を示します。"),
        SpreadPosition("outcome", "最終結果", "全体の流れが行き着きやすい未来の姿や、到達しやすい結末を示します。"),
    ],
    position_labels=(
        "現在",
        "課題",
        "顕在意識",
        "潜在意識",
        "過去",
        "近未来",
        "助言",
        "環境",
        "願望/恐れ",
        "結果",
    ),
)

ALL_SPREADS: dict[str, Spread] = {
    ONE_CARD.id: ONE_CARD,
    THREE_CARD_SITUATION.id: THREE_CARD_SITUATION,
    HEXAGRAM.id: HEXAGRAM,
    CELTIC_CROSS.id: CELTIC_CROSS,
}

__all__ = [
    "SpreadPosition",
    "Spread",
    "ONE_CARD",
    "THREE_CARD_SITUATION",
    "HEXAGRAM",
    "CELTIC_CROSS",
    "ALL_SPREADS",
]
