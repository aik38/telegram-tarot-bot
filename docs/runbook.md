# 運用切り戻し手順（Phase8/9/10 MVP向け）

既存の占い/相談の文体や出力フォーマットを変えずに、運用で最低限対応するための手順だけをまとめています。すべての操作は国内βのSQLite構成を前提にしています。

## 即時リリース/切り戻しトグル
- **課金を止める**: `.env` または環境変数で `PAYWALL_ENABLED=false` にして bot を再起動。占い文面はそのまま、チケット消費/パス判定のみ無効化されます。
- **負荷を落とす**: `THROTTLE_MESSAGE_INTERVAL_SEC` / `THROTTLE_CALLBACK_INTERVAL_SEC` を一時的に上げて再起動し、連打を吸収します（例: 2.0 / 1.2）。
- **画像オプションを隠す**: `IMAGE_ADDON_ENABLED=false` でボタンが「準備中」表示に戻ります。

## Bot/API の再起動
1. `.env` を見直し（TOKEN/API_KEY/ADMIN_USER_IDS/PAYWALL_ENABLED）。
2. プロセスを停止してから `python -m bot.main` を再起動（または supervisor/systemd を再起動）。
3. 起動ログで `DB health check: ok` と `polling=True` を確認。

## DB バックアップ/復元（SQLite）
- バックアップ: `cp db/telegram_tarot.db db/telegram_tarot.db.bak_$(date +%Y%m%d%H%M)` を取得（実行前に bot 停止推奨）。
- 復元: bot を止め、`cp db/telegram_tarot.db.bak_YYYYMMDDHHMM db/telegram_tarot.db` で戻す。起動後に `pytest -q` か `/admin stats` で最低限の整合を確認。

## 決済トラブル時の運用
- **重複/未反映**: `/admin grant <user_id> <SKU>` で手動付与し、`/status` 案内を送る。ログは audits/payment_events に残る。
- **返金**: Telegram 決済 ID を確認し `/refund <telegram_payment_charge_id>` を実行。成功メッセージをユーザーへ転送。
- **一時停止**: `PAYWALL_ENABLED=false` にして再起動。相談/占いは無料のまま継続。

## フィードバックとインシデントメモ
- ユーザーからの声: `/feedback <text>` で受け付け。管理者は `/admin feedback_recent 10` で確認。
- 簡易ヘルス/件数: `/admin stats 7` で日次の占い/相談/決済/エラー件数を取得（直近14日まで指定可能）。
- 障害時の返信テンプレ（チャットで送る）:
  - 「ただいま調整中です。ご不便をおかけしてごめんなさい。少し時間をおいて再度お試しください。」
  - 決済後の未反映は「/status で付与状況を確認いただき、反映していない場合はこのままお知らせください」と追記。

## 参考ドキュメント
- `docs/sqlite_backup.md`: SQLite バックアップ詳細。
- `docs/launch_checklist.md`: 本番反映前の確認リスト。
- `docs/payment_states.md`: 決済ステートとエラー時の扱い。
