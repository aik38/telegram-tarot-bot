# SQLite バックアップ / リストア手順（運用メモ）

決済・利用状況は `users` / `payments` / `payment_events` テーブルで管理しているため、バックアップと復旧は **DBファイルを一貫した状態で取得・戻す** ことが重要です。以下は最小手順です。

## 前提

- サービス停止中に実施する（Bot / API のプロセスを止める）
- デフォルトパス: `SQLITE_DB_PATH`（未指定時は `db/telegram_tarot.db`）

## バックアップ

### 運用停止 → ファイルコピー

1. Bot / API を停止する。
2. DBファイルをコピーする。
   ```bash
   cp db/telegram_tarot.db backups/telegram_tarot_$(date +%Y%m%d%H%M%S).db
   ```
3. コピー先のハッシュを残す（改ざん検知用・オプション）。
   ```bash
   sha256sum backups/telegram_tarot_*.db | tee backups/sha256sums.txt
   ```

### sqlite3 の `.backup` コマンドを使う場合

オンラインバックアップが必要な場合は `.backup` を利用する。

```bash
sqlite3 db/telegram_tarot.db ".backup 'backups/telegram_tarot_$(date +%Y%m%d%H%M%S).db'"
```

## リストア

1. Bot / API を停止する。
2. 現行ファイルを退避する（上書きリスク低減）。
   ```bash
   mv db/telegram_tarot.db db/telegram_tarot.db.bak.$(date +%Y%m%d%H%M%S)
   ```
3. 取得済みバックアップを戻す。
   ```bash
   cp backups/telegram_tarot_YYYYmmddHHMMSS.db db/telegram_tarot.db
   ```
4. パーミッションと所有者を確認する（実行ユーザーが読める/書けること）。
5. Bot / API を起動し、`python -m pytest -q` または簡易 `/status` 表示で整合性を確認する。

## ワンページ復旧パス

1. サービス停止
2. `cp backups/... db/telegram_tarot.db`
3. サービス起動 → `/status` でチケット・パス・最新購入が表示されるか確認

以上で完了。
