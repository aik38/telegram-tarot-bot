# Telegram Tarot Bot

Telegram向けタロット占いボットのミニマルな開発用セットアップです。このREADMEは入口ガイドで、進行状況やタスクの最新情報は `docs/WBS.md`（唯一のWBS）を参照してください。スナップショットは `docs/WBS_PROGRESS.md` に残しています。
価格設計やローンチ前チェックリストは `docs/pricing_notes.md` と `docs/launch_checklist.md`（MVP向け48hチェックリスト、冒頭に30〜60分のショートラン手順あり）を参照してください。運用時の SQLite バックアップ/リストア手順は `docs/sqlite_backup.md` にまとめています。

## 最初にやること（30〜60分ショートラン）
`docs/launch_checklist.md` のショートラン手順を起点に、以下の3ステップで MVP ローンチを最短確認します。

1. `pytest -q`
2. `python -m bot.main`
3. Telegram で `/start` `/help` `/buy` `/status` を確認

マーケ素材、SNS整備、監視ダッシュボード等は「ローンチ後」に回して問題ありません。ショートラン後は同じ `docs/launch_checklist.md` の 48h チェックリストを STEP3 として実行してください。

## インストール / 開発ルーチン（telegram sync）

```bash
pip install -r requirements.txt
```

- 日常運用は PowerShell で `tools/sync.ps1`（ショートカット名: “telegram sync”）を実行する想定です。内部で `git pull --rebase` → `.venv\Scripts\python.exe -m pytest -q` → 変更があれば commit/push の順で回します。
  - Windows 由来の junk（Desktop.ini など）だけが差分の場合は commit をスキップします（PR #47 実装）。

### 主な環境変数

- `.env.example` を `.env` にコピーして値を埋めてください。
- `SUPPORT_EMAIL`: 利用規約やサポート案内に表示するメールアドレス。未設定時は `hasegawaarisa1@gmail.com` が使われますが、ダミー表記を避けるため環境変数で上書きする運用を推奨します。
- `THROTTLE_MESSAGE_INTERVAL_SEC` / `THROTTLE_CALLBACK_INTERVAL_SEC`: テキスト送信・ボタン連打それぞれの最小間隔（秒）。未設定時は 1.2s / 0.8s のままです。負荷試験時に環境変数で調整してください。

### シークレット運用ルール

- `.env` を含むシークレットファイルはコミットしないでください（`.env.example` のみを追跡対象にします）。
- ログや print で BOT_TOKEN / OPENAI_API_KEY などの値を直接出力しないでください。`core.logging.SafeLogFilter` がコンソールと `logs/bot.log` でトークンをマスクするので、開発時はこのロガーを経由する形を維持してください。
- 調査でシークレット値を扱う場合は、メモやスクリーンショットにも残さない運用を徹底してください。

### 管理者ID（ADMIN_USER_IDS）の設定

- 管理者にしたい Telegram アカウントの **個人チャットの Chat ID** を取得します。
  - 例: RawDataBot (`@raw_data_bot` など) で `/start` し、表示される `id` の値を控える。
- `ADMIN_USER_IDS` はカンマ区切りで複数指定できます。
  - 例: `1357890414,123456789`
- PowerShell での起動例:

  ```powershell
  cd "...\telegram-tarot-bot"
  .\.venv\Scripts\Activate.ps1
  $env:ADMIN_USER_IDS="1357890414"
  python -m bot.main
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
- 利用規約と安全ガイドは `/terms` または `/help` から辿れます。

- コマンド：`/read1`（1枚引き）、`/read3`（3枚引き）、`/hexa`（ヘキサグラム）、`/celtic`（ケルト十字）
  - `/read3` はスリーカード（3枚固定）で、1枚目=過去、2枚目=現在、3枚目=未来の時間軸。時間スケール指定がない場合は前後3か月を想定し、流れ・傾向・気づきを示す。出力は見出しなしで `《カード》：` 行を3つ並べ、箇条書きは未来（3枚目）のみ最大3点、断定を避けた提案ベースでまとめる。
  - `/love1` `/love3` は旧コマンドとして互換対応しています。

スリーカード（/read3）の出力イメージ（概念例）:

《カード》：カップの3（正位置）
過去の場面で得た安心感がいまの選択にも響いていそうです。
《カード》：ソードの8（逆位置）
視点を少し変えるだけで、ほどける余地があります。
《カード》：ワンドのペイジ（正位置）
- 気になる誘いがあれば、まず話を聞いてみるときっかけになりそうです。
- 手軽に始められる準備を一つ決め、肩慣らしをしてみてください。
- 迷ったら「なぜ気になるか」を言葉にしてから次の手順を選ぶと動きやすそうです。

### 決済と権限

- `/buy` で Stars (XTR) の商品一覧を表示します。ボタンから決済フローに進みます。
- `/status` でパスの有効期限やチケット残数を確認できます。
- `PAYWALL_ENABLED=true` のとき `/read3` `/hexa` `/celtic` は有料メニュー扱いになります（`/love3` は旧コマンドとして互換対応）。
  - 有効なパス（premium_until が現在より未来）または対応するチケット残高があれば利用可能です。
  - パスが無効でチケットもない場合は実行せず `/buy` を案内します。

## 課金導線スモークテスト（連打含む）

- 前提: テスト用の決済設定を行い、PAYWALL_ENABLED を本番同等に設定する。
- `/buy` で購入メニューを開き、商品ボタンを連打しても Bot が落ちないこと（コンソールに `query is too old` が出ても動作継続する）。
- 同じ商品ボタンを短時間に連打した場合、「購入画面は既に表示しています」と案内され、Invoice が重複発行されないこと。
- 決済確認（pre_checkout_query）は即時に応答し、例外が起きてもプロセスが落ちないこと。
- 決済完了後に「購入ありがとう」「付与内容」「占いに戻る/ステータスを見る」ボタンが表示され、占い導線に戻れること。
- `/status` または「📊ステータスを見る」ボタンで、パス期限・チケット残数・無料枠の次回リセット時刻が1画面で確認できること。
- パスが有効なユーザーは「スリーカード(3枚)」購入ボタンを押しても追加課金に進まず、占いに戻るよう案内されること。

### BotFather 推奨コマンド

`/setcommands` で登録しておく推奨リストです。

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

## よくあるエラー（Troubleshooting）

- `TelegramConflictError: terminated by other getUpdates request` が出る場合は、**同じ BOT トークンで polling が二重起動している**（または webhook と競合している）ことが多いです。
  - 対処: 旧プロセスを停止し、polling 運用では `deleteWebhook` を実行してから、同時に1インスタンスだけ起動するようにしてください。

## タロットロジックの内部構造

- `core/tarot/cards.py`
  - 大アルカナ22枚・小アルカナ56枚のカード定義（ID、和名・英名、正逆キーワードなど）
- `core/tarot/spreads.py`
  - 1枚引きと3枚引き（状況・障害・未来）のスプレッド定義
- `core/tarot/draws.py`
  - スプレッドに応じてカードをランダムに抽選する `draw_cards`、正逆表記ヘルパー

Bot からはスプレッドを選び `draw_cards` を呼ぶだけで、カードと正逆のセットが得られます。

## 二重モードの使い方例

- 通常チャット例（タロット用語は禁止）
  - 入力: `最近仕事で疲れています。`
  - 出力: カウンセリング寄りの励ましや提案。カード名やタロット用語は出さない。
- 占いモード例（カード名＋正逆を必ず提示）
  - 入力: `最近仕事がきついので、今後について占ってほしいです。`
  - 出力: `引いたカードは次の通りです…` とカード名・正位置/逆位置を列挙し、その後でリーディングを提供。

### 仕様メモ

- 通常チャットでは「占って」「タロット」「カードを引いて」などの明確な依頼がない限り、占い・カードの話題は出さない。
- 通常チャットの返答にタロット用語が紛れた場合は自動的にリライトし、再度含まれる場合は該当文を削除して安全に返す。
- タロット占いモードでは回答の先頭で必ず引いたカード名と正逆を明示する。
- 断定的な表現は避け、落ち着いた敬語で安心感のあるトーンを保つ。

### テスト

system python だと `pytest` が見つからない場合があるため、必ず venv を前提に実行してください。

1) `.venv` を有効化して実行する場合

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest -q
```

2) 有効化せずに venv の python を直指定する場合

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```
# akolasia_tarot_bot 起動メモ

## セットアップ
cd "%USERPROFILE%\OneDrive\デスクトップ\telegram-tarot-bot"
.\.venv\Scripts\Activate
pip install -r requirements.txt

## 起動
cd "%USERPROFILE%\OneDrive\デスクトップ\telegram-tarot-bot"
.\.venv\Scripts\Activate
python -m bot.main

###　Codexで修正後のプル・プッシュ

cd "$env:USERPROFILE\OneDrive\デスクトップ\telegram-tarot-bot"; `
git pull --rebase origin main; `
git add .; `
git commit -m "Update tarot bot from local"; `
git push origin main

## Dev routine (daily)
1) Run `tools/sync.ps1` (= telegram sync): `git pull --rebase` → `.venv\Scripts\python.exe -m pytest -q` → 変更があれば commit/push（junk だけなら commit しない）。
2) Pick next item from `docs/WBS.md` (Next 10 tasks)
3) Use Codex (web) to implement 1 task per PR
4) After merge: run sync again and smoke-test `/start` `/buy` `/status`

## Launch checklist (public + marketing start)
詳細は `docs/launch_checklist.md` に集約。進行状況とWBSは `docs/WBS.md` を参照してください。

## 次に見るドキュメント
- `docs/WBS.md`: 唯一のWBS（進行中タスクと優先度）
- `docs/WBS_PROGRESS.md`: 進捗スナップショット
- `docs/launch_checklist.md`: ショートラン＆48hチェックリスト
- `docs/runbook.md`: 運用・トラブルシュート
- `docs/pricing_notes.md`: 価格と課金まわりのメモ
