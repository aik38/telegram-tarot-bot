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
# akolasia_tarot_bot 起動メモ

## セットアップ
cd "%USERPROFILE%\OneDrive\デスクトップ\telegram-tarot-bot"
.\.venv\Scripts\Activate
pip install -r requirements.txt

## 起動
cd "%USERPROFILE%\OneDrive\デスクトップ\telegram-tarot-bot"
.\.venv\Scripts\Activate
python -m bot.main
