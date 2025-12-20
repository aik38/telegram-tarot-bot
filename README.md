# Telegram Tarot Bot

Telegram 向けタロット占いボットの開発・運用ガイドです。進行中タスクは **`docs/WBS.md`**（唯一のWBS）を参照し、履歴は `docs/WBS_PROGRESS.md` に蓄積しています。ローンチ前チェックは `docs/launch_checklist.md`、価格や Stars 設定は `docs/pricing_notes.md` を参照してください。

---

## Quickstart（venv → install → .env → run）

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                 # BOT_TOKEN / OPENAI_API_KEY などをセット
python -m bot.main                   # Bot を起動
```

API を使う場合は別ターミナルで `uvicorn api.main:app --reload --port 8000` を実行します。

### 環境変数のポイント
- `SUPPORT_EMAIL`: /terms などに表示。デフォルトのダミーを上書きしてください。
- `THROTTLE_MESSAGE_INTERVAL_SEC` / `THROTTLE_CALLBACK_INTERVAL_SEC`: 送信・ボタン連打の最小間隔（秒）。負荷試験時に調整。
- シークレット（`.env`）はコミット禁止。ログは `core.logging.SafeLogFilter` 経由でマスクされます。

### 管理者 ID
`ADMIN_USER_IDS` に Telegram の Chat ID をカンマ区切りで指定すると管理者向け機能が有効になります。

---

## Runbook（よく使うコマンド）
- Bot 起動: `python -m bot.main`
- API 起動: `uvicorn api.main:app --reload --port 8000`
- 日常の sync（Windows 想定）: `tools/sync.ps1` で `git pull --rebase` → `pytest -q` → 差分があれば commit/push（junk は除外）
- 推奨 BotFather コマンド登録:
  ```
  start - ボットの案内
  buy - 有料メニュー購入
  status - 利用状況の確認
  terms - 利用規約の表示と同意
  support - お問い合わせ窓口
  paysupport - 決済トラブル対応窓口
  read1 - 1枚引き
  read3 - 3枚引き
  hexa - ヘキサグラム（7枚）
  celtic - ケルト十字（10枚）
  ```

---

## Tests
- コンパイルチェック: `python -m compileall bot tests tools`
- 単体・回帰: `pytest -q`
- 翻訳キー整合: `python tools/check_translation_keys.py`（英語を基準に ja/pt の missing/extra を検出）

---

## Multilingual（/lang と Language ボタン）
- `/lang` またはメニューの **Language** ボタンから ja/en/pt を切替。翻訳テーブルは `bot/texts/en.py` / `bot/texts/ja.py` / `bot/texts/pt.py` にあり、`bot/texts/i18n.py` が正規化・選択を担当します。
- 翻訳キーの追加・削除を行った場合は、必ず `python tools/check_translation_keys.py` と `pytest -q` を実行して差分が 0 であることを確認してください。
- 既知の課題: まれに Language ボタンが無反応になる報告あり。callback の応答ログを確認し、問題が再現した場合は `lang:set:*` のハンドラと throttle/dedup ガードの突合を行ってください（WBS Backlog に修正タスクを追加済み）。

---

## Payments / Stars スモーク手順
- `/buy` で商品一覧 → ボタン連打でも落ちないことを確認（重複発行は防止される）。
- `/status` でパス期限・チケット残高・無料枠リセット時刻が 1 画面で見えること。
- `PAYWALL_ENABLED=true` 時、パスか対応チケットが無ければ有料メニューは案内のみ。パスが有効なユーザーが同じ商品を押しても追加課金に進まないことを確認。
- 決済完了後に「購入ありがとう」「付与内容」「占いに戻る/ステータスを見る」が表示され、占い導線に戻れること。

---

## Troubleshooting
- `TelegramConflictError: terminated by other getUpdates request`  
  - 原因: 同じ BOT トークンで polling が二重起動（または webhook と競合）。  
  - 対処: 旧プロセス停止 → `deleteWebhook` 実行 → 単一インスタンスで再起動。
- 「Language」ボタンが反応しない  
  - まれに callback ack が届かない報告あり。`lang:set:*` イベントのログを確認し、dedup/throttle 設定を併せて確認してください。
- 重複応答を防ぎたい  
  - `tests/test_deduplication_guards.py` の回帰観点を参考に、同一 `message_id` で複数処理しないことを確認。

---

## Bot の使い方（モードとコマンド）
- 通常チャット: タロット用語を出さず、相談モードで返答。
- 占いモード: `/read1` `/read3` `/hexa` `/celtic`（`/love1` `/love3` は旧互換）。回答冒頭でカード名と正逆を明示し、断定を避けた提案ベースで返します。
- 利用規約・安全ガイド: `/terms` または `/help` から参照。

タロットの内部実装は `core/tarot/cards.py`（カード定義）、`core/tarot/spreads.py`（スプレッド）、`core/tarot/draws.py`（抽選ロジック）を参照してください。

---

## 参考ドキュメント
- `docs/WBS.md` / `docs/WBS_PROGRESS.md`: 進行中タスクと履歴
- `docs/launch_checklist.md`: ショートラン & 48h チェック
- `docs/runbook.md`: 運用・トラブルシュート
- `docs/pricing_notes.md`: Stars/価格メモ
- `docs/sqlite_backup.md`: SQLite バックアップ・リストア
