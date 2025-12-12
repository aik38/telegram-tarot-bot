# WBS


---

## 2. 開発WBS（MVP向け）

次に、MVP実装向けの作業分解（WBS）の雛形です。  
タスクIDをつけて、Codex側で参照しやすくしてあります。

```markdown
# WBS - Telegram Tarot Bot (MVP)

## フェーズ0: プロジェクト骨組み

- T0-01: リポジトリ初期化（Git）
- T0-02: ディレクトリ構成作成（bot/, api/, core/, db/, docs/, tests/）
- T0-03: Python仮想環境・requirements.txt / pyproject.toml 作成
- T0-04: `.env.example` と `core/config.py` の雛形作成
- T0-05: `AGENTS.md` / `README.md` / 基本説明ドキュメント追加

## フェーズ1: 最小動作（/start → 挨拶 & healthチェック）

- T1-01: aiogram による `bot/main.py` 作成 (`/start` ハンドラのみ)
- T1-02: FastAPI による `api/main.py` 作成 (`GET /api/health` で "OK" を返す)
- T1-03: ログ設定（core/logging.py）実装
- T1-04: 開発用起動スクリプト（scripts/dev_run_bot.sh, scripts/dev_run_api.sh）作成
- T1-05: ローカルで Bot と API が起動し、基本動作を確認

## フェーズ2: タロットカード・スプレッドロジック

- T2-01: `core/tarot/cards.py` に78枚＋正逆のカード定義を実装
- T2-02: `core/tarot/spreads.py` に1枚引き・3枚引き等のスプレッド定義を実装
- T2-03: カードID／名称／正逆を扱うデータ構造の設計
- T2-04: Tarotロジックの単体テスト（tests/test_tarot_basic.py）作成

## フェーズ3: 会話フロー（MVP）

- T3-01: テーマ選択用のInlineKeyboardを実装（恋愛/仕事/人間関係/お金/その他）
- T3-02: ユーザー質問入力ステップ（フリーテキスト）を実装
- T3-03: スプレッド選択ステップ（1枚/3枚など）を実装
- T3-04: スプレッドに応じたカード抽選ロジックをBot側に組み込み
- T3-05: 抽選結果をテキストでユーザーへ表示
- T3-06: 会話状態（テーマ／質問／スプレッド／カード）をメモリ or DB に一時保存

## フェーズ4: LLM連携API

- T4-01: `POST /api/v1/tarot/reading` エンドポイントをFastAPI側に実装
- T4-02: リクエストスキーマ（Pydanticモデル）とレスポンススキーマ定義
- T4-03: OpenAI/互換APIへのLLM呼び出しロジック実装（core/services/llm_client.py 等）
- T4-04: タロット用プロンプトテンプレートの設計・実装
- T4-05: Bot側からAPIへのHTTP呼び出し（aiohttp or httpx）実装
- T4-06: APIレスポンスをユーザー向けメッセージに変換して返信

## フェーズ5: DB設計・永続化（SQLiteベータ）

- T5-01: DB_SCHEMA.md をもとに schema.sql / ORM モデルを作成
- T5-02: `users` / `sessions` / `messages` / `tarot_draws` 基本4テーブルの実装
- T5-03: Bot側で、ユーザー情報・セッション情報を保存
- T5-04: API側で、LLMリクエスト・レスポンスを `messages` 等に記録
- T5-05: 簡易なクエリ（ユーザーごとの最新セッション取得 等）の追加

## フェーズ6: ログ・イベント・監査

- T6-01: `app_events` テーブル実装（イベント種別・タイムスタンプ・プロパティJSON）
- T6-02: LP→Bot開始→占い完了までの主要イベントを記録（LPは将来用）
- T6-03: `audits` テーブル実装（重要操作の監査ログ）
- T6-04: LLM入出力の要約ログ（プロンプト全文ではなく要約）を必要に応じて保存

## フェーズ7: β運用準備（日本語UI）

- T7-01: 国内クローズドβ用のメッセージ文言整備（日本語）
- T7-02: `.env` で `ENV=jp-beta`, `LANG_DEFAULT=ja` での起動確認
- T7-03: 制限ユーザーのみがアクセスできるよう、簡易IP制限・Botリンク制御検討
- T7-04: 基本的なエラーハンドリング・タイムアウト・リトライ

## フェーズ8: 海外本番への布石（設計のみ）

- T8-01: 言語切替用のi18n設計（messages_ja.py / messages_en.py 等）の草案作成
- T8-02: 通貨・決済設計（payments / entitlements テーブル）の詳細設計
- T8-03: Telegram Bot Payments / Stripe Webhook用エンドポイント仕様整理
