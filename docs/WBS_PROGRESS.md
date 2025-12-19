# WBS_PROGRESS - 2025-05-06 (payment flow stabilization audit)

目的: 決済導線の安定化が main にマージされた状態を棚卸しし、canonical WBS（docs/WBS.md）を更新したスナップショット。

## 追加進捗
- T1-05: テーマ別の質問例を拡充し、/help から辿れるように整理。(bot/main.py L130-L205, L1345-L1346; bot/texts/ja.py L1-L15; tests/test_bot_modes.py L71-L80)

## 今回完了扱いにした主な項目
- /buy の導線と重複購入防止（dedup TTL + invoice 多重抑止）を確認。(bot/main.py L431-L447, L1187-L1449)
- pre_checkout → successful_payment → 付与 → /status 導線が一連で動くことを確認。(bot/main.py L1490-L1560; core/db.py L214-L392)
- /status が trial残日数・パス期限・チケット残数を一画面で返すことを確認。(bot/main.py L900-L970)
- スタートアップログ・例外処理が落ちずに動作することを再確認。(core/logging.py L1-L26; bot/main.py L182-L208, L450-L520, L2006-L2023)

## まだ未着手/要補完の主要ポイント
- 返金/失敗時の状態遷移表と通知、手動付与/剥奪の運用は未整備。(bot/main.py L1563-L1599)
- 決済イベントの永続化・監視、callback 連打時の追加レート制限は未着手。
- /status への購入履歴表示や stale callback 時のユーザー再案内は未実装。

## 次に着手すべき10タスク
- docs/WBS.md の「Next 10 tasks」を参照（価格確定、案内文強化、決済イベントログ、テスト追加など）。
