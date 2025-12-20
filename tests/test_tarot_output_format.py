from bot.main import CAUTION_NOTE
from bot.utils.tarot_output import finalize_tarot_answer


def _get_last_bullet_index(lines: list[str]) -> int:
    for idx in range(len(lines) - 1, -1, -1):
        if lines[idx].startswith("・"):
            return idx
    return -1


def test_finalize_removes_meta_and_normalizes_card_line():
    raw = (
        "【メインメッセージ】\n"
        "メインメッセージ: ここから始めます。\n"
        "まとめとして、冒頭の導入です。\n"
        "引いたカード：愚者（逆位置）\n"
        "\n"
        "逆位置の愚者は自由さを示します。\n"
        "・まず 相手を観察する\n"
        "・次に 距離を大切にする\n"
        "結論として、信頼を育てましょう。"
    )

    result = finalize_tarot_answer(raw)
    lines = result.splitlines()

    assert sum(1 for line in lines if line.startswith("《カード》：")) == 1
    assert all("メインメッセージ" not in line for line in lines)
    assert all("まとめとして" not in line for line in lines)
    assert lines[-1].startswith("・")
    assert lines[-2].startswith("・")


def test_finalize_limits_card_line_to_first_one():
    raw = (
        "カード：魔術師（正位置）\n"
        "《カード》：女帝（逆位置）\n"
        "・行動を始める\n"
        "・創造性を大切にする"
    )

    result = finalize_tarot_answer(raw)
    lines = result.splitlines()

    assert lines.count("《カード》：魔術師（正位置）") == 1
    assert all("女帝" not in line for line in lines if line.startswith("《カード》："))


def test_finalize_drops_summary_after_bullets():
    raw = (
        "導入の文章です。\n"
        "引いたカード: 月（正位置）\n"
        "説明を続けます。\n"
        "・ポイントを整理する\n"
        "・足元を固める\n"
        "\n"
        "要するに、落ち着いて進めましょう。"
    )

    result = finalize_tarot_answer(raw)
    lines = result.splitlines()
    last_bullet_idx = _get_last_bullet_index(lines)
    assert last_bullet_idx != -1
    assert all(line == "" for line in lines[last_bullet_idx + 1 :])


def test_finalize_preserves_caution_note():
    raw = (
        "はじめに状況を整理します。\n"
        "カード: 太陽（正位置）\n"
        "温かな光が差す状況です。\n"
        "・前向きな姿勢を保つ\n"
        "・周囲と喜びを分かち合う\n\n"
        f"{CAUTION_NOTE}"
    )

    result = finalize_tarot_answer(raw, caution_note=CAUTION_NOTE)

    assert result.endswith(CAUTION_NOTE)
    assert CAUTION_NOTE in result.split("\n\n")[-1]
    assert "要するに" not in result
