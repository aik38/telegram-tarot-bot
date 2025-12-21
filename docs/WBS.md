# WBS - Telegram Tarot Bot（canonical, post-payment flow stabilization）

このドキュメントを **唯一のWBS** とし、進捗スナップショットは `docs/WBS_PROGRESS.md` に記録します（最終更新: 2025-12-21 UTC）。見た目よりも「落ちない」「迷子にならない」を最優先で維持します。

## ⏩ 現在地（Today）
- Telegram表示の装飾（`**` など）除去・空白整形を完了（文章/絵文字は維持）。
- 購入導線は `/buy -> Stars` に一本化済み。
- 「🔮鑑定中です…」メッセージは回答生成後に確実に削除されるよう修正済み。
- Launch 48h checklist / ショートラン（30〜60分）は `docs/launch_checklist.md` で運用。

## 🎯 今やる（MVP必須）
- STEP3: `docs/launch_checklist.md` の 48h checklist を実行する（所要目安: 約90分、成果物: ログ/スクショ/結果メモを残す）。
  - 実施済みの項目はこのブロックで [x] にし、成果物はスクショ→`screenshots/`、ログ→`logs/`、補足メモ→`docs/WBS_PROGRESS.md` に残す。

## ⏳ 後回し（ローンチ後）
- フェーズ8Aの文面微調整（T8A-04/05/06）はローンチ後でOK。マーケ文体統一や購入導線の心理整備は後追いで実施。
- フェーズ8B（LP）、フェーズ9（キャラクター設計）、フェーズ10（マーケ・グロース）は全てローンチ後に回す。

## ✅ Done（完了条件つき）
- [x] T3-09: 待機メッセージのクリーンアップ。完了条件: 回答生成後に「🔮鑑定中です…（しばらくお待ちください）」が確実に削除されるよう安全な delete ヘルパーを導入し、main にマージ済み。
- [x] T8A-02: スリーカード（過去/現在/未来）時間軸フォーマットを固定。完了条件: /read3 出力が `《カード》：` 行3つ＋役割固定で見出しなし、箇条書きは未来のみ最大3点になるよう finalizer で強制し、bot/main.py にマージ済み。
- [x] 出力制約テスト: 《カード》行/禁止語/箇条書き位置の自動検証。完了条件: `tests/test_drawn_cards_format.py` で《カード》3回・見出し禁止語なし・箇条書きは3枚目のみ最大3件で green を確認できる。
- [x] T3-08: 同一ユーザー並行セッションのロック/待機案内を統一（bot/main.py のユーザー別 lock + queued 表示で順番処理に集約）。
- [x] T4-06: レスポンス後処理（長文カット/改行整形）を共通化し、call_openai_with_retry に適用（bot/utils/postprocess.py）。
- [x] T5-06: 返金/失敗/二重決済の状態遷移と通知をドキュメント化し、コードと整合（docs/payment_states.md, bot/main.py の dedup + refund ハンドリング）。
- [x] T5-07: 管理者の手動付与/剥奪と監査ログ（/admin grant, /admin revoke → core/db.py audits）を実装。
- [x] T7-01: リクエスト単位で追える request_id 付きログとシークレットマスク（core/logging.py, RequestIdMiddleware）。
- [x] T7-05: レート制限（ユーザー別：秒間/分間）閾値を環境変数化し、案内文言も調整済み。
- [x] T7-06: シークレット管理（env 読み込みとログマスク）を README/launch_checklist と tests/test_logging_masking.py で運用固定。

## 🚫 Not doing（理由つき）
- T3-07: 相談モード仕様確定（回数制限と文体）は現行仕様を維持する方針が固まっており、本サイクルでは再設計しない。フェーズ9/10 での改善余地があれば別タスクで検討し、それまでは凍結。
- T4-07: 料金最適化（モデル選定、max_tokens、キャッシュ、リトライ）は gpt-4o-mini＋環境変数しきい値の現行運用を維持する。コスト方針は既定のため追加実装なし。フェーズ9/10 での見直しまで凍結。
- T8B-01: LP を作るか（作るなら1ページ）。理由: 国内クローズドβでは外部LPを使った集客を行わないため公開判断まで凍結。

## 🔥 Next 10 tasks（優先度順・完了条件つき）
1. [ ] T8A-04: 相談モードの価値定義（短文・共感・行動提案）。完了条件: 現行の相談モード文体を守りつつ、価値の説明・できること/できないこと・簡易提案例が docs/ux_copy.md と /help の案内文にまとまる（コード挙動は維持）。
2. [ ] T8A-05: “購入”の心理導線（無料→体験→不足→解決）。完了条件: /start, /buy, /status の文面テンプレを docs/ux_copy.md に揃え、無料枠からの誘導が1画面で伝わることをステージングで確認（UIロジック変更なし）。
3. [ ] T8A-06: メッセージ文体の統一（丁寧でやさしい敬語）。完了条件: bot/texts/ja.py の主要案内（/help, 入力エラー）が同じトーンで揃い、docs/ux_copy.md にスタイルガイドを残す。
4. [~] T4-02: タロット用プロンプトテンプレ（安定した型）。完了条件: core/prompts.py のテンプレと期待アウトラインを docs/WBS_PROGRESS.md で固定し、LLM 出力の型揺れを抑制するユニットテストの TODO を切り出す（フォーマット自体は変更しない）。
5. [ ] T4-08: API分離の要否（Bot直呼び vs FastAPI経由）。完了条件: 直呼び継続 or FastAPI 経由のどちらかを決め、測定方法とロールバック手順を docs/launch_checklist.md / docs/runbook.md に追記。
6. [ ] T5-09: 不正対策（複垢/同端末/再インストール）。完了条件: 端末・アカウントの異常検知ルールと `/admin` での即時対応手順を docs/runbook.md に追記。
7. [ ] T5-10: コスト監視（ユーザー別トークン/日次上限）。完了条件: OpenAI usage の日次ダンプ手順（手動/cron）と閾値アラートの目視運用を docs/kpi.md or README に記載。
8. [ ] T6-03: sessions（会話セッション）永続化。完了条件: セッション開始/完了/タイムアウトを記録する軽量テーブル案を db/schema.sql にまとめ、ダウングレード手順を docs/WBS_PROGRESS.md に残す（実装は最小）。
9. [ ] T6-07: app_events（イベント計測：start/reading_done/buy_click…）。完了条件: /admin stats で見たいイベント一覧と保存カラムを docs/kpi.md に定義し、bot 停止なしで失敗を無視する実装方針を決める。
10. [ ] T7-04: 監視（ヘルスチェック/死活監視/通知）。完了条件: Bot/Polling の死活確認手順（手動 curl or /health の有無）と通知チャネルを docs/runbook.md にまとめ、当日の当番がすぐ試せる状態にする。

## 🚀 Launch (public + marketing) - 48h checklist

詳細と手順は `docs/launch_checklist.md` に集約。WBS 側では進捗と成果物の置き場所だけを管理する。

- 成果物の置き場所: スクショ→`screenshots/`、ログ→`logs/`、運用メモ→`docs/WBS_PROGRESS.md`。
- ショートラン（30〜60分）の合否判定は `docs/launch_checklist.md` 冒頭を参照。

- [ ] T-48h: PowerShell で `tools/sync.ps1` を実行 → `pytest -q` green を確認し、コンソールログを `logs/` に保存。
- [ ] T-48h: `.env` 本番値（BOT_TOKEN / OPENAI_API_KEY / 管理者ID / PAYWALL）を確認し、`PAYWALL_ENABLED` の初期状態と切替タイミングを runbook にメモ。
- [ ] T-36h: SQLite backup/restore 手順を読み上げテストし、復旧コマンドをチャンネル共有（`cp` の具体例つき）。
- [ ] T-24h: 決済スモーク（/buy→購入→/status 反映、/buy 連打で dedup、stale callback の案内安全性）。失敗時の手動付与/返金手順を runbook で再確認。
- [ ] T-12h: /start と /help の文面を最新テンプレ（docs/ux_copy.md）で確認し、質問例・料金・次アクションが1画面で伝わることをステージングでスクショ。
- [ ] T-6h: SNS（X/IG）プロフィール/固定投稿/リンク導線を完成。価値提案 1 文と購入導線を docs/marketing.md から引用。
- [ ] T-3h: Bot を再起動し `logs/bot.log` に rid 付きで出力されることを確認、/admin stats で直近件数を確認。
- [ ] T-0: 公開告知（3投稿）→ 24h 監視（ログ/決済/離脱点）→ 翌日小修正。障害時は runbook「初動テンプレ」に沿って応答。

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
- [x] T3-07: 相談モード仕様確定（回数制限と文体）― 現行の相談モード回数制限/文体を維持する方針で確定（再設計は行わない）。
- [x] T3-08: 同一ユーザーの並行セッション扱い（bot/main.py のユーザー別ロックで並列受付を順次化し、案内を返す）

---

## フェーズ4: LLM 連携（プロンプト・安全・コスト）
- [x] T4-01: OpenAI へのAPI呼び出し（200 OK）(bot/main.py L485-L520)
- [~] T4-02: タロット用プロンプトテンプレ（安定した型）(core/prompts.py)
- [x] T4-03: “箇条書き数”のガイダンスをLLM出力に反映 (bot/main.py L1003-L1078)
    - [x] T4-04: テーマ別プロンプト分岐（恋愛/仕事/人生…）(PR #46; core/prompts.py L67-L73; bot/main.py L1346-L1393)
- [x] T4-05: NG/危険領域の制御（医療/法律/自傷他害）(PR #44; bot/main.py L171-L248, L293-L333, L1005-L1036, L2169-L2234; tests/test_safety_topics.py L1-L34)
- [x] T4-06: レスポンス後処理（長文カット/要点先出し/改行整形）（bot/utils/postprocess.py を共通化し call_openai_with_retry に適用）
- [x] T4-07: 料金最適化（モデル選定、max_tokens、キャッシュ、リトライ）― 現行の gpt-4o-mini＋しきい値運用で固定（追加改変なし）。
- [ ] (!) T4-08: API分離の要否（Bot直呼び vs FastAPI経由）

---

## フェーズ5: 課金・制限（収益化の中核）
- [x] T5-01: 無料枠（trial）回数・リセット仕様（1日/5日）(bot/main.py L700-L743)
- [x] T5-02: /status（残回数・次回リセット・期限表示）(bot/main.py L900-L970, L1356-L1370)
- [x] T5-03: /buy（チャージ導線）文面とUI (bot/main.py L1187-L1449)
- [x] T5-04: 決済方式の確定（Telegram Stars/XTR）(bot/main.py L900-L908, L1440-L1447)
- [x] T5-05: 決済完了→権限付与（entitlements）実装 (bot/main.py L1490-L1560; core/db.py L214-L392)
- [x] T5-06: 返金/失敗/二重決済の扱い（状態遷移表）(docs/payment_states.md; bot/main.py L1563-L1599; core/db.py L255-L286)
- [x] T5-07: 管理者で手動付与/剥奪（トラブル対応）(/admin grant / revoke 実装と audits で記録)
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
- [x] T7-01: ログ整備（request単位で追える）(core/logging.py L1-L26; bot/main.py L2006-L2023) ― request_id 付きフィルタとシークレットマスクを全ハンドラに適用済み。
- [x] T7-02: 例外ハンドリング（OpenAI失敗/タイムアウト/429、callback/pre_checkout）(bot/main.py L182-L208, L450-L475, L485-L520)
- [x] T7-03: リトライ方針（OpenAIリトライ3回＋バックオフ）(bot/main.py L485-L520)
- [ ] T7-04: 監視（ヘルスチェック/死活監視/通知）
- [x] T7-05: レート制限（ユーザー別：秒間/分間）(bot/main.py L44-L54; ThrottleMiddleware) ― core/config.py の閾値設定＋文言更新＋tests/test_throttle.py で連打時の案内を確認。
- [x] T7-06: シークレット管理（.env読み込み、ログへの鍵非出力）(core/config.py) ― core/logging.py のマスクユーティリティ強化＋tests/test_logging_masking.py で検証＋README/launch_checklist に運用ルール追記。

---

## フェーズ8: “フロント”＝ユーザー体験（Telegram内UX + 外部LP）
### 8-A Telegram内UX（最重要）
- [x] T8A-01: 最初の60秒UX（3タップで占い完了／下部4ボタンの一本道）(bot/main.py L1335-L1374, L1975-L2044; PR #6: クイックメニュー常時表示の補強＋回帰テスト追加／下部4ボタンの現行デザイン維持)
- [x] T8A-02: 結果の見せ方（PR7代替: スリーカードの時間軸フォーマットを固定。過去/現在/未来の3枚役割を明示し、見出し禁止・`《カード》：` 行が3回・箇条書きは3枚目のみ最大3点を強制するフォーマット制御を集約。テストでカード行数/禁止語/箇条書き位置を確認済み）(PR #54)
    - 出力冒頭は「《カード》：カード名（正/逆位置）」の3行で、役割（過去/現在/未来）が入れ替わらないよう固定表示し、見出し・題名は付けない
    - 結論段落と箇条書きが重複しないよう統合し、箇条書きは未来カードのみ最大3点に抑える
    - 断定を避け、流れ・傾向・気づきを中心に読みやすさを維持する
- [x] T8A-03: 続き導線（深掘り質問/3枚アップセル）(bot/main.py L1091-L1178, L1478-L1486)
- [x] T8A-07: フィードバック回収導線（/feedback + /admin feedback_recent）。完了条件: user_id/mode/request_id 付きでSQLiteに保存し、管理者が最新件数を確認できる（bot/main.py, core/db.py）。
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
- [x] T10-09: 運用切り戻し runbook。完了条件: PAYWALL/スロットル調整、SQLiteバックアップ/復元、Bot再起動、障害返信テンプレが docs/runbook.md にまとまっている。
- [x] T10-10: 最小メトリクス可視化。完了条件: /admin stats で日次の占い/相談/決済/エラー件数をSQLite集計から取得できる（core/db.py app_events + payments）。

---

## フェーズ8-10: MVPローンチ最短経路（運用寄せの小タスク）
1. [ ] 相談モードの価値説明とトーン統一（T8A-04/06）― docs/ux_copy.md と /help の文面を同期し、丁寧語で統一する。
2. [ ] 購入導線テンプレの一本化（T8A-05）― /start,/buy,/status の案内を docs/ux_copy.md に揃え、ステージングで確認。
3. [ ] 価値提案 1 文と投稿テンプレ（T10-01/03）― docs/marketing.md をもとに SNS 投稿を準備。
4. [ ] KPI しきい値の目視運用（T10-05）― docs/kpi.md に沿って /admin stats と OpenAI Usage の見方を固定。
5. [ ] 監視・切り戻し手順の明文化（T7-04 + runbook）― 死活確認と通知先、PAYWALL 切替手順をチェックリストに沿って実演。

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
