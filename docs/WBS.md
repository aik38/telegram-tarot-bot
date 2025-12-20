# WBS - Telegram Tarot Bot（canonical, post-payment flow stabilization）

このドキュメントを **唯一のWBS** とし、進捗スナップショットは `docs/WBS_PROGRESS.md` に記録します（最終更新: 2025-05-06 UTC）。見た目よりも「落ちない」「迷子にならない」を最優先で維持します。

## Next 10 tasks（優先度順・完了条件つき）
1. [ ] T3-07: 相談モード仕様確定（回数制限と文体）。完了条件: 相談モードの UX/回数制限/文体が固まり、/help または README で案内できる。
2. [ ] T3-08: 同一ユーザーの並行セッション扱い。完了条件: 同一ユーザーの並行対話に対するロック/キュー/上書き方針が決まり、bot/main.py に実装される。
3. [~] T4-02: タロット用プロンプトテンプレ（安定した型）。完了条件: core/prompts.py のテンプレが安定し、LLM 出力の型揺れを抑制するユニットテストが追加される。(core/prompts.py)
4. [ ] T4-06: レスポンス後処理（長文カット/要点先出し/改行整形）。完了条件: bot/main.py に後処理ロジックが入り、長文暴走を抑制できる。
5. [ ] T4-07: 料金最適化（モデル選定、max_tokens、キャッシュ、リトライ）。完了条件: LLM のコスト指標が可視化され、運用ルールが README か docs に明記される。
6. [~] T5-06: 返金/失敗/二重決済の扱い（状態遷移表）。完了条件: 返金・失敗・二重決済時の状態図と通知シナリオが docs に追加され、テストで主要パスをカバーする。(bot/main.py L1563-L1599; core/db.py L255-L286)
7. [ ] T5-07: 管理者で手動付与/剥奪（トラブル対応）。完了条件: 管理者が手動で付与/剥奪でき、監査ログが残る。
8. [~] T7-01: ログ整備（request単位で追える）。完了条件: 構造化ログか相当の追跡方法が入り、主要イベントが request_id で紐付けられる。(core/logging.py L1-L26; bot/main.py L2006-L2023)
9. [~] T7-05: レート制限（ユーザー別：秒間/分間）。完了条件: ThrottleMiddleware のしきい値/通知文言が調整され、連打でも UX を崩さない。
10. [~] T7-06: シークレット管理（.env 読み込み、ログへの鍵非出力）。完了条件: シークレット取扱ルールが docs に明記され、不要な出力が抑止される。(core/config.py)

## 記号ルール
- `[ ]` 未着手 / ToDo
- `[~]` 進行中・要補完
- `[x]` 完了（根拠を括弧に記載）
- `(!)` 判断待ち

## Safety notes（禁止/注意テーマ）
- 以下は占いで断定せず、専門家/公的窓口を案内する: 医療・診断/薬、法律・契約/紛争、投資助言、暴力・他害、自傷/強い不安。
- /help と /terms から禁止/注意テーマにリンクし、bot/main.py の安全ガード（build_sensitive_topic_notice / respond_with_safety_notice）で自動案内します。(bot/main.py L171-L248, L293-L333, L1005-L1036, L2169-L2234; bot/texts/ja.py L1-L15; tests/test_safety_topics.py L1-L34)

## 備考（運用メモ）
- Windows 由来の junk ファイルは `.gitignore` と `tools/sync.ps1` のフィルタで無視済み（PR #47）。

## 現状ハイライト（payment flow stabilizing の確認結果）
- Invoice多重発行の抑止と stale callback 吸収が入っている（dedup TTL＋`_safe_answer_callback/_safe_answer_pre_checkout`）。(bot/main.py L182-L208, L431-L447, L450-L475, L1393-L1449)
- pre_checkout → successful_payment → 権限付与 → /status 導線が成立し、購入後の戻り先ボタンも提供。(bot/main.py L1490-L1561; core/db.py L214-L392)
- /status は trial残日数・パス期限・チケット残数を1画面に集約し、管理者モードにも対応。(bot/main.py L900-L970, L1356-L1370)
- 決済系の連打耐性: callback throttle=0.8s + purchase dedup TTL=30s を明示し、stale時は「チャージへ」ボタン付き再案内を自動送出。(bot/main.py `_check_purchase_dedup`, `_handle_stale_interaction`)

---

## フェーズ0: 土台（リポジトリ・設定・品質の最低ライン）
- [x] T0-01: リポジトリ初期化（Git）
- [x] T0-02: ディレクトリ構成（bot/, api/, core/, db/, docs/, tests/）
- [x] T0-03: venv / requirements（起動できる状態）
- [x] T0-04: `.env.example` と設定読み込みの雛形（最低限）
- [x] T0-05: 基本ドキュメント（README / docs の追加）
- [x] T0-06: ローカル起動手順の固定（README に python -m bot.main / uvicorn の手順）(README.md L11-L34)
- [x] T0-07: 不要ファイル・未使用定義の整理（旧メニュー/スプレッドUI削除済み）

---

## フェーズ1: Bot 最小UX（/start・メニュー・コマンド導線）
- [x] T1-01: `/start`（挨拶＋使い方）(bot/main.py L1335-L1341)
- [x] T1-02: メニュー（占い / 相談 / チャージ / ステータス 導線）(bot/main.py L1335-L1374)
- [x] T1-03: `help`/`terms`/`support`/`paysupport` の整備 (bot/main.py L1226-L1308)
- [x] T1-04: 入力ガード（空入力・長文等でも崩れない）(bot/utils/validators.py)
- [x] T1-05: 例文（質問の例）をテーマ別に最小セット (bot/main.py L130-L205, L1345-L1346; bot/texts/ja.py L1-L15; tests/test_bot_modes.py L71-L80)
- [x] T1-06: 多重送信対策（連打・同時リクエストのキュー/ロック）(bot/main.py L342-L420)
- [x] T1-07: “戻る/やり直し”導線（テーマ選択に戻る、メニュー復帰）(bot/main.py L1343-L1374)
- [x] T1-08: 管理者用コマンド拡充（/admin grant など）(bot/main.py L1706-L1777; tests/test_bot_modes.py L281-L310)

---

## フェーズ2: タロット基盤（カード・スプレッド・抽選・表示）
- [x] T2-01: 78枚＋正逆のカード定義（ID/名称/キーワード）(core/tarot/cards.py L1-L196)
- [x] T2-02: スプレッド定義（1枚/3枚/7枚/10枚）(core/tarot/spreads.py L1-L68; bot/main.py L646-L689)
- [x] T2-03: 抽選ロジック（箇条書き数 action_count の抽選）(core/tarot/draws.py; bot/main.py L559-L608)
- [x] T2-04: “引いたカード”表示フォーマット固定（card line + 整形）(PR #43; bot/main.py L1171-L1186; tests/test_drawn_cards_format.py L28-L74)
    - [x] T2-05: スプレッドごとの役割語彙テンプレ (PR #46; core/tarot/spreads.py L14-L128)
- [x] T2-06: 単体テスト（カード整合性・抽選分布・フォーマット）(PR #43; tests/test_drawn_cards_format.py L28-L74)
- [x] T2-07: 禁止/注意テーマの扱い（医療/法律/投資）(PR #44; bot/main.py L171-L248, L293-L333, L1005-L1036, L2169-L2234; bot/texts/ja.py L1-L15; tests/test_safety_topics.py L1-L34)

---

## フェーズ3: 会話フロー（状態管理・分岐・再入）
- [x] T3-01: テーマ選択（InlineKeyboard）(bot/main.py L1457-L1476)
- [x] T3-02: 質問入力（フリーテキスト）(bot/main.py L1975-L2044)
- [x] T3-03: スプレッド選択（1枚固定の一本道／アップセルボタン）(bot/main.py L1478-L1486, L1659-L1726)
- [x] T3-04: 会話状態（theme/question/spread）を保持 (bot/main.py L1000-L1089)
- [x] T3-05: “途中で別コマンド”が来たときの状態リセットルール (PR #45; bot/main.py L769-L838, L1504-L1669; tests/test_bot_modes.py L202-L229)
- [x] T3-06: タイムアウト（一定時間で状態破棄）(PR #45; bot/main.py L101-L130, L824-L838, L2355-L2393; tests/test_bot_modes.py L215-L229)
- [ ] T3-07: 相談モード仕様確定（回数制限と文体）
- [ ] T3-08: 同一ユーザーの並行セッション扱い

---

## フェーズ4: LLM 連携（プロンプト・安全・コスト）
- [x] T4-01: OpenAI へのAPI呼び出し（200 OK）(bot/main.py L485-L520)
- [~] T4-02: タロット用プロンプトテンプレ（安定した型）(core/prompts.py)
- [x] T4-03: “箇条書き数”のガイダンスをLLM出力に反映 (bot/main.py L1003-L1078)
    - [x] T4-04: テーマ別プロンプト分岐（恋愛/仕事/人生…）(PR #46; core/prompts.py L67-L73; bot/main.py L1346-L1393)
- [x] T4-05: NG/危険領域の制御（医療/法律/自傷他害）(PR #44; bot/main.py L171-L248, L293-L333, L1005-L1036, L2169-L2234; tests/test_safety_topics.py L1-L34)
- [ ] T4-06: レスポンス後処理（長文カット/要点先出し/改行整形）
- [ ] T4-07: 料金最適化（モデル選定、max_tokens、キャッシュ、リトライ）
- [ ] (!) T4-08: API分離の要否（Bot直呼び vs FastAPI経由）

---

## フェーズ5: 課金・制限（収益化の中核）
- [x] T5-01: 無料枠（trial）回数・リセット仕様（1日/5日）(bot/main.py L700-L743)
- [x] T5-02: /status（残回数・次回リセット・期限表示）(bot/main.py L900-L970, L1356-L1370)
- [x] T5-03: /buy（チャージ導線）文面とUI (bot/main.py L1187-L1449)
- [x] T5-04: 決済方式の確定（Telegram Stars/XTR）(bot/main.py L900-L908, L1440-L1447)
- [x] T5-05: 決済完了→権限付与（entitlements）実装 (bot/main.py L1490-L1560; core/db.py L214-L392)
- [~] T5-06: 返金/失敗/二重決済の扱い（状態遷移表）(bot/main.py L1563-L1599; core/db.py L255-L286) ― 返金コマンドはあるが状態図と通知は未整備。
- [ ] T5-07: 管理者で手動付与/剥奪（トラブル対応）
- [x] T5-08: 価格表（商品ID・内容・回数・有効期限）を設定ファイル化 (core/store/catalog.py L1-L72)
- [ ] T5-09: 不正対策（複垢/同端末/再インストール）
- [ ] T5-10: コスト監視（ユーザー別トークン/日次上限）

---

## フェーズ6: DB・永続化（最低限の観測と再現性）
- [x] T6-01: SQLite（β）で DB 初期化（schema.sql or ORM）(core/db.py L73-L152)
- [x] T6-02: users（ユーザー基本情報）(core/db.py L154-L213)
- [ ] T6-03: sessions（会話セッション）
- [ ] T6-04: messages（入出力ログ：要点だけ）
- [ ] T6-05: tarot_draws（引いたカード・正逆・スプレッド）
- [x] T6-06: entitlements（購入/残回数/期限）(core/db.py L214-L392)
- [ ] T6-07: app_events（イベント計測：start/reading_done/buy_click…）
- [ ] T6-08: audits（重要操作ログ：付与/剥奪など）
- [ ] T6-09: DB マイグレーション方針（簡易でOK：1ファイルでも可）

---

## フェーズ7: 信頼性（落ちない・迷子にしない）
- [~] T7-01: ログ整備（request単位で追える）(core/logging.py L1-L26; bot/main.py L2006-L2023) ― 主要イベントは残るが構造化ログ未整備。
- [x] T7-02: 例外ハンドリング（OpenAI失敗/タイムアウト/429、callback/pre_checkout）(bot/main.py L182-L208, L450-L475, L485-L520)
- [x] T7-03: リトライ方針（OpenAIリトライ3回＋バックオフ）(bot/main.py L485-L520)
- [ ] T7-04: 監視（ヘルスチェック/死活監視/通知）
- [~] T7-05: レート制限（ユーザー別：秒間/分間）(bot/main.py L44-L54; ThrottleMiddleware) ― 追加チューニング余地あり。
- [~] T7-06: シークレット管理（.env読み込み、ログへの鍵非出力）(core/config.py) ― 運用ルールの明文化が未。

---

## フェーズ8: “フロント”＝ユーザー体験（Telegram内UX + 外部LP）
### 8-A Telegram内UX（最重要）
- [x] T8A-01: 最初の60秒UX（3タップで占い完了／下部4ボタンの一本道）(bot/main.py L1335-L1374, L1975-L2044; PR #6: クイックメニュー常時表示の補強＋回帰テスト追加)
- [ ] T8A-02: 結果の見せ方（結論→理由→行動、読みやすさ最優先）
- [x] T8A-03: 続き導線（深掘り質問/3枚アップセル）(bot/main.py L1091-L1178, L1478-L1486)
- [ ] T8A-04: 相談モードの価値定義（短文・共感・行動提案）
- [ ] T8A-05: “購入”の心理導線（無料→体験→不足→解決）
- [ ] T8A-06: メッセージ文体の統一（丁寧でやさしい敬語）

### 8-B 外部LP（任意：やるなら最小）
- [ ] (!) T8B-01: LP を作るか（作るなら1ページ）
- [ ] T8B-02: LP 必須：価値/使い方/料金/免責/リンク（Botへ）
- [ ] T8B-03: 計測（UTM/クリック/開始率）

---

## フェーズ9: キャラクター設計（人格＝ブランド）
- [ ] T9-01: キャラ設定シート（口調・価値観・NG・得意領域）
- [ ] T9-02: キャラの“約束”（安心・安全の約束）
- [ ] T9-03: テーマ別キャラの振る舞い（恋愛＝寄り添い、仕事＝整理…）
- [ ] T9-04: 例文ライブラリ（開始/深掘り/断り/購入誘導/お礼）
- [ ] T9-05: 画像アセット方針（アイコン/ヘッダー/OGP）
- [ ] T9-06: 文章スタイルガイド（短文/中文/長文の型）

---

## フェーズ10: マーケ・グロース（計測できる施策だけ）
- [ ] T10-01: 価値提案を1文で固定（誰の何をどう解決するか）
- [ ] T10-02: 流入チャネル設計（X/Instagram/Telegram/Note 等）
- [ ] T10-03: 投稿テンプレ（週7本作れる型：悩み→解決→導線）
- [ ] T10-04: 招待/紹介導線（紹介コード・特典）
- [ ] T10-05: KPI設計（開始率/完了率/課金率/継続率/粗利）
- [ ] T10-06: A/B（文面/価格/無料枠）を“最小”で回す
- [ ] T10-07: クリエイティブ生成フロー（画像/短文/動画の作り方）
- [ ] T10-08: 炎上・規約リスク回避（NG表現チェック）

---

## フェーズ11: リリース準備（β→公開）
- [~] T11-01: launch_checklist.md の更新・運用 (docs/launch_checklist.md)
- [ ] T11-02: 利用規約/免責/プライバシー（最小）
- [ ] T11-03: 本番環境のデプロイ先決定（VPS/クラウド）
- [ ] T11-04: バックアップ（DB/ログ）
- [ ] T11-05: “壊れたときの復旧手順”を1枚にまとめる

---

## フェーズ12: 改善サイクル（運用の型）
- [ ] T12-01: 週次レビュー（KPI→仮説→修正→検証）
- [ ] T12-02: 失敗ログの型（失敗理由カテゴリを決める）
- [ ] T12-03: コスト監視（月次：原価率・上限アラート）
- [ ] T12-04: 施策バックログ（次の一手を常に3つ持つ）

## Launch (public + marketing) - 48h checklist

- [ ] T-48h: `tools/sync.ps1` を実行して `pytest` green を確認（ログ保存）
- [ ] T-48h: `.env` 本番値（BOT_TOKEN / OPENAI_API_KEY / 管理者ID / PAYWALL）を再確認
- [ ] T-24h: 決済スモーク（/buy→購入→/status反映、/buy連打、stale callback）
- [ ] T-24h: SQLite backup/restore 手順を一回“読み上げテスト”（復旧の想像がつく状態に）
- [ ] T-12h: /start と /help の文面最終化（質問例・料金・次アクションが明確）
- [ ] T-6h: SNS（X/IG）プロフィール/固定投稿/リンク導線を完成
- [ ] T-0: 公開告知（3投稿）→ 24h 監視（ログ/決済/離脱点）→ 翌日小修正
