# Telegram Tarot Bot

Telegram向けタロット占いボットのミニマルな開発用セットアップです。

## インストール

```bash
pip install -r requirements.txt
```

## 開発環境での起動方法

- Bot 起動: `python -m bot.main`
- API 起動: `uvicorn api.main:app --reload --port 8000`

### ログ出力

- Bot 起動時に `logs/bot.log` に INFO 以上のログがローテーション付きで保存されます。
- コンソールにも同じログが出力されるため、開発中はどちらでも確認できます。

### Bot の使い方メモ

- メッセージに「占って」と入れると、タロット占いモードでカードを引いて返答します。
- それ以外のメッセージには、雑談や相談に答える通常の会話モードで返信します。
- 例）`今の恋愛運を占ってほしい` → タロットモード、`今日はしんどかった…ちょっと話を聞いて` → 通常会話モード。
# akolasia_tarot_bot 起動メモ

## セットアップ
cd "%USERPROFILE%\OneDrive\デスクトップ\telegram-tarot-bot"
.\.venv\Scripts\Activate
pip install -r requirements.txt

## 起動
cd "%USERPROFILE%\OneDrive\デスクトップ\telegram-tarot-bot"
.\.venv\Scripts\Activate
python -m bot.main
