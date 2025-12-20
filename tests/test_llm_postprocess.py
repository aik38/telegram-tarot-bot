from bot.utils.postprocess import postprocess_llm_text


def test_postprocess_normalizes_whitespace() -> None:
    raw = "  《カード》：魔術師（正位置）  \n\n\n  要点 を整理します。 \n  \n  ・ 行動を始める  "
    result = postprocess_llm_text(raw)

    assert "\n\n\n" not in result
    assert result.splitlines()[0] == "《カード》：魔術師（正位置）"
    assert result.endswith("・ 行動を始める") or result.endswith("・行動を始める")


def test_postprocess_soft_cuts_when_too_long() -> None:
    long_body = "長文が続きます。" * 300
    result = postprocess_llm_text(long_body)

    assert "途中までお届けしました" in result
    assert result.startswith("長文が続きます。")
    note_length = len("（文章がとても長かったため途中までお届けしました。続きが必要でしたら、もう一度聞いてくださいね。）")
    assert len(result) <= 2000 + note_length + 2
