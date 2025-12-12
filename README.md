# Telegram Tarot Bot

Telegram向けタロット占いボットのミニマルな開発用セットアップです。

## インストール

```bash
pip install -r requirements.txt
```

## 開発環境での起動方法

- Bot 起動: `python -m bot.main`
- API 起動: `uvicorn api.main:app --reload --port 8000`
