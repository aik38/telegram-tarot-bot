# WBS - Telegram Tarot Bot（canonical, post-payment flow stabilization）

このドキュメントを **唯一のWBS** とし、進捗スナップショットは `docs/WBS_PROGRESS.md` に記録します。
「落ちない」「迷子にならない」を最優先で維持します。（最終更新: 2025-12-21）

---

## ⏩ 現在地（Today）
- main: `origin/main` と同期済み / working tree clean
- テスト: `python -m compileall bot tests` ✅ / `pytest -q` ✅（101 passed）
- 多言語: 翻訳キー差分 0 ✅（ja/pt vs en）
- ログ: 直近で危険パターン（TelegramBadRequest 等）の頻発なし ✅
- 直近マージ（重要）:
  - PR #79/#80: 多言語カバレッジ強化（用語/サポート系の参照統一、不足JP補完）
  - ステータスメッセージ cleanup 強化（delete失敗時のフォールバック edit/log）
  - 翻訳キー整合性のテスト/CLI 追加（差分の早期検出）
  - 重複アップデート防止ガード（同一 message_id の二重処理抑止）＋回帰テスト
  - Language ボタンがまれに無反応になる報告あり（callback ack/重複ガードの再確認が必要）— Backlog に修正タスクを追加

---

## ✅ Done（直近で追加された“重要な完了”）
- [x] 翻訳テーブルの参照統一（support/terms 系を共通辞書経由に）
- [x] 翻訳キー整合性チェックの導入
  - テスト: `tests/test_translation_keys.py`
  - ツール: `tools/check_translation_keys.py`（英語を基準に missing/extra を検出）
- [x] ステータスメッセージ cleanup の堅牢化
  - delete 失敗時に edit へフォールバック、ログ強化
- [x] 重複処理ガードの導入（同一 message_id の二重返信/二重処理を抑止）
  - 回帰テスト: `tests/test_deduplication_guards.py`

---

## 🎯 今やる（ローンチ直前の“ショートラン”）
> 目的：本番前に「落ちない・迷子にならない」を短時間で再確認し、証跡を残す。

### ✅ ショートラン（30〜60分）— ここまで実施済み
- [x] compileall: `python -m compileall bot tests`
- [x] tests: `pytest -q`
- [x] 翻訳キー差分: `python tools/check_translation_keys.py`（or 等価チェック）で missing/extra = 0
- [x] ログ grep（危険パターン）で未検出

### ⏳ 残り（実機スモーク）
- [ ] Bot 起動: `python -m bot.main`（または運用の起動手順）
- [ ] /start → 言語選択 → ja/en/pt それぞれで初回メッセージが自然
- [ ] 占い（/read1, /read3）で「カードを引かない」事故が出ない
- [ ] 相談モード（短文/共感/行動提案）が崩れない
- [ ] /buy → /status 導線が成立（購入前/購入後、二重タップ耐性）
- [ ] 「🔮鑑定中…」の消し忘れが出ない（失敗時は edit で復旧してログが残る）

証跡の置き場所:
- スクショ→`screenshots/`
- ログ→`logs/`
- 運用メモ→`docs/WBS_PROGRESS.md`

---

## 🔥 Next 10 tasks（フェーズ8〜10＝ローンチの勝ち筋）
1. [ ] T8A-04: 相談モードの価値定義（短文・共感・行動提案）
   - 完了条件: docs/ux_copy.md に「できること/できないこと/例文/導線」が揃う（挙動変更は不要）
2. [ ] T8A-05: 購入の心理導線（無料→体験→不足→解決）
   - 完了条件: /start /buy /status の説明が 1画面で理解できる（文面整備）
3. [ ] T8A-06: 文体統一（丁寧でやさしい敬語）
   - 完了条件: 主要案内＆エラーが同じトーン。スタイルガイドを docs/ux_copy.md に残す
4. [ ] T9-01: キャラ設定シート（口調・価値観・NG・得意領域）
5. [ ] T9-04: 例文ライブラリ（開始/深掘り/断り/購入誘導/お礼）
6. [ ] T9-06: 文章スタイルガイド（短文/中文/長文の型）
7. [ ] T10-01: 価値提案を1文で固定（日本語/英語）
8. [ ] T10-02: 流入導線（X/Instagram/Telegram）— IGはリンク5枠の最適配置
9. [ ] T8A-07: Language ボタン無反応の修正（callback ack + dedup/throttle 突合テスト追加）
10. [ ] T10-08: 炎上・規約リスク回避（NG表現チェックのルール化）

---

## 🅿 Parking / Deferred
- [ ] T10-03: 投稿テンプレ（週7本の型）＋固定ポスト文面（ローンチ前のバグ修正を優先するため一時待機。進行履歴は docs/WBS_PROGRESS.md 2025-12-21 エントリ参照）

---

## 記号ルール
- `[ ]` 未着手 / ToDo
- `[~]` 進行中・要補完
- `[x]` 完了
- `(!)` 判断待ち

---

## Safety notes（禁止/注意テーマ）
- 占いで断定しない: 医療・診断/薬、法律・契約/紛争、投資助言、暴力・他害、自傷/強い不安
- /help /terms から注意事項にリンクし、安全ガードで自動案内する（現行方針維持）
